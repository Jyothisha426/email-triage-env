# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import random
import copy

from models import (
    EmailObservation, EmailAction, StepResult,
    EnvState, ResetResult, TaskInfo
)
from tasks import TASKS, EMAILS

app = FastAPI(
    title="Email Triage Environment",
    description=(
        "An OpenEnv-compatible RL environment where an AI agent learns "
        "to triage emails: classify spam, detect urgency, and write professional replies."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session state ───────────────────────────────────
_session = {
    "task_name": None,
    "email_queue": [],
    "current_email_idx": 0,
    "step_number": 0,
    "cumulative_reward": 0.0,
    "done": False,
    "history": [],
}


# ── Accept task_name as JSON body (not query param) ───────────
class ResetRequest(BaseModel):
    task_name: str = "spam_classification"


def _get_current_email() -> dict:
    idx = _session["current_email_idx"]
    return _session["email_queue"][idx]


def _build_observation(email: dict, task_name: str, step_number: int) -> EmailObservation:
    task_info = TASKS[task_name]["info"]
    return EmailObservation(
        email_id=email["email_id"],
        subject=email["subject"],
        body=email["body"],
        sender=email["sender"],
        task_name=task_name,
        task_description=task_info["description"],
        step_number=step_number,
    )


def _clamp_score(score: float) -> float:
    """Ensure score is strictly between 0 and 1."""
    return round(min(max(score, 0.01), 0.99), 4)


# ════════════════════════════════════════════════════════════
# ENDPOINT: Health check
# ════════════════════════════════════════════════════════════
@app.get("/health")
def health():
    return {"status": "ok", "environment": "email-triage"}


# ════════════════════════════════════════════════════════════
# ENDPOINT: List tasks
# ════════════════════════════════════════════════════════════
@app.get("/tasks", response_model=list[TaskInfo])
def list_tasks():
    return [TaskInfo(**task["info"]) for task in TASKS.values()]


# ════════════════════════════════════════════════════════════
# ENDPOINT: Reset — accepts JSON body with task_name
# ════════════════════════════════════════════════════════════
@app.post("/reset", response_model=ResetResult)
def reset(request: ResetRequest = None):
    """
    Start a fresh episode. Accepts task_name in JSON body.
    Also works with no body (defaults to spam_classification).
    """
    # Handle both JSON body and no-body calls
    task_name = request.task_name if request else "spam_classification"

    if task_name not in TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{task_name}'. Available: {list(TASKS.keys())}"
        )

    shuffled = copy.deepcopy(EMAILS)
    random.shuffle(shuffled)

    _session.update({
        "task_name": task_name,
        "email_queue": shuffled,
        "current_email_idx": 0,
        "step_number": 1,
        "cumulative_reward": 0.0,
        "done": False,
        "history": [],
    })

    first_email = _session["email_queue"][0]
    obs = _build_observation(first_email, task_name, step_number=1)

    return ResetResult(
        observation=obs,
        info={
            "task": task_name,
            "total_emails": len(EMAILS),
            "message": f"Episode started. Process {len(EMAILS)} emails for task '{task_name}'.",
        }
    )


# ════════════════════════════════════════════════════════════
# ENDPOINT: Step — agent submits an action
# ════════════════════════════════════════════════════════════
@app.post("/step", response_model=StepResult)
def step(action: EmailAction):
    if _session["task_name"] is None:
        raise HTTPException(status_code=400, detail="Call /reset first to start an episode.")

    if _session["done"]:
        raise HTTPException(status_code=400, detail="Episode is already done. Call /reset to start a new one.")

    task_name = _session["task_name"]
    current_email = _get_current_email()

    # ── Grade the action ──────────────────────────────────────
    grader = TASKS[task_name]["grader"]
    reward, feedback = grader(action.response, current_email)

    # ── Clamp reward strictly between 0 and 1 ────────────────
    reward = _clamp_score(reward)

    _session["cumulative_reward"] += reward
    _session["history"].append({
        "step": _session["step_number"],
        "email_id": current_email["email_id"],
        "agent_response": action.response[:100],
        "reward": reward,
        "feedback": feedback,
    })

    # ── Advance to next email ─────────────────────────────────
    next_idx = _session["current_email_idx"] + 1
    done = next_idx >= len(_session["email_queue"])
    _session["done"] = done

    if not done:
        _session["current_email_idx"] = next_idx
        _session["step_number"] += 1
        next_email = _get_current_email()
        next_obs = _build_observation(next_email, task_name, _session["step_number"])
    else:
        next_obs = _build_observation(current_email, task_name, _session["step_number"])

    # ── Compute normalised final score (strictly 0-1) ─────────
    steps_done = len(_session["history"])
    final_score = _clamp_score(_session["cumulative_reward"] / steps_done) if steps_done > 0 else 0.01

    return StepResult(
        observation=next_obs,
        reward=reward,
        done=done,
        info={
            "feedback": feedback,
            "email_id": current_email["email_id"],
            "cumulative_reward": _session["cumulative_reward"],
            "score": final_score,
            "steps_remaining": len(_session["email_queue"]) - next_idx,
        }
    )


# ════════════════════════════════════════════════════════════
# ENDPOINT: State
# ════════════════════════════════════════════════════════════
@app.get("/state", response_model=EnvState)
def state():
    if _session["task_name"] is None:
        raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")

    task_info = TASKS[_session["task_name"]]["info"]
    steps_done = len(_session["history"])
    score = _clamp_score(_session["cumulative_reward"] / steps_done) if steps_done > 0 else 0.01

    return EnvState(
        task_name=_session["task_name"],
        step_number=_session["step_number"],
        total_steps=task_info["max_steps"],
        cumulative_reward=score,
        done=_session["done"],
    )


# ════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=False)