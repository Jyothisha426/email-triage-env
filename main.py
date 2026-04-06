# main.py
# ─────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS:
#   This is the environment SERVER. It exposes HTTP endpoints
#   that the agent (and OpenEnv's evaluator) calls:
#
#     POST /reset          → start a new episode, get first email
#     POST /step           → submit an action, get reward + next email
#     GET  /state          → peek at current state
#     GET  /tasks          → list all available tasks
#     GET  /health         → ping (must return 200 for HF Spaces check)
#
#   We use FastAPI because it's fast, auto-generates docs at /docs,
#   and works perfectly with Pydantic models (automatic validation).
# ─────────────────────────────────────────────────────────────

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
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

# Allow cross-origin requests (needed for HF Spaces + external callers)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session state ───────────────────────────────────
# Each "session" tracks where we are in the episode.
# In production you'd use Redis, but for this hackathon
# a single global state is fine (one agent at a time).
_session = {
    "task_name": None,
    "email_queue": [],         # shuffled list of emails for this episode
    "current_email_idx": 0,
    "step_number": 0,
    "cumulative_reward": 0.0,
    "done": False,
    "history": [],
}


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


# ════════════════════════════════════════════════════════════
# ENDPOINT: Health check
# ════════════════════════════════════════════════════════════
@app.get("/health")
def health():
    """
    The OpenEnv evaluator pings this URL first.
    Must return HTTP 200 or you're disqualified.
    """
    return {"status": "ok", "environment": "email-triage"}


# ════════════════════════════════════════════════════════════
# ENDPOINT: List tasks
# ════════════════════════════════════════════════════════════
@app.get("/tasks", response_model=list[TaskInfo])
def list_tasks():
    """Returns metadata about all 3 tasks."""
    return [
        TaskInfo(**task["info"])
        for task in TASKS.values()
    ]


# ════════════════════════════════════════════════════════════
# ENDPOINT: Reset — start a new episode
# ════════════════════════════════════════════════════════════
@app.post("/reset", response_model=ResetResult)
def reset(task_name: str = Query(default="spam_classification")):
    """
    Start a fresh episode for the given task.
    Shuffles the email queue so each run is different.
    Returns the first email for the agent to process.
    """
    if task_name not in TASKS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown task '{task_name}'. Available: {list(TASKS.keys())}"
        )

    # Shuffle emails so the agent can't memorize order
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
    """
    The agent submits its answer for the current email.
    We grade it, record the reward, then advance to the next email.
    If all emails are processed, done=True.
    """
    if _session["task_name"] is None:
        raise HTTPException(status_code=400, detail="Call /reset first to start an episode.")

    if _session["done"]:
        raise HTTPException(status_code=400, detail="Episode is already done. Call /reset to start a new one.")

    task_name = _session["task_name"]
    current_email = _get_current_email()

    # ── Grade the action ──────────────────────────────────────
    grader = TASKS[task_name]["grader"]
    reward, feedback = grader(action.response, current_email)

    # ── Update session ────────────────────────────────────────
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
        # Episode over — return final observation (same email, done=True)
        next_obs = _build_observation(current_email, task_name, _session["step_number"])

    return StepResult(
        observation=next_obs,
        reward=reward,
        done=done,
        info={
            "feedback": feedback,
            "email_id": current_email["email_id"],
            "cumulative_reward": _session["cumulative_reward"],
            "steps_remaining": len(_session["email_queue"]) - next_idx,
        }
    )


# ════════════════════════════════════════════════════════════
# ENDPOINT: State — inspect current episode state
# ════════════════════════════════════════════════════════════
@app.get("/state", response_model=EnvState)
def state():
    """Returns a snapshot of the current episode state."""
    if _session["task_name"] is None:
        raise HTTPException(status_code=400, detail="No active episode. Call /reset first.")

    task_info = TASKS[_session["task_name"]]["info"]
    return EnvState(
        task_name=_session["task_name"],
        step_number=_session["step_number"],
        total_steps=task_info["max_steps"],
        cumulative_reward=_session["cumulative_reward"],
        done=_session["done"],
    )


# ════════════════════════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7860, reload=False)
