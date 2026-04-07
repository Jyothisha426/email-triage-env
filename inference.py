#!/usr/bin/env python3
"""
inference.py — Email Triage Environment Agent
─────────────────────────────────────────────
The evaluator runs this file and checks:
  1. stdout contains [START] / [STEP] / [END] blocks in EXACT text format
  2. Scores are in 0.0–1.0 range
  3. Finishes in under 20 minutes
  4. No crashes

MANDATORY LOG FORMAT (validator regex-parses these lines):
  [START] task=TASKNAME
  [STEP] step=N reward=R.RRRR
  [END] task=TASKNAME score=S.SSSS steps=N
"""

import os
import sys
import asyncio
import httpx
from openai import OpenAI

# ── Configuration from environment variables ──────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api-inference.huggingface.co/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "mistralai/Mistral-7B-Instruct-v0.3")
HF_TOKEN     = os.environ.get("HF_TOKEN",     "")
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "https://jyothisha426-email-triage-env.hf.space")

# ── Tasks to run ──────────────────────────────────────────────────────────────
TASKS_TO_RUN = [
    "spam_classification",
    "urgency_detection",
    "professional_reply",
]

MAX_STEPS = 6  # max emails per task episode


# ════════════════════════════════════════════════════════════════════════════════
# LOGGING — MANDATORY FORMAT — DO NOT CHANGE THESE PRINT STATEMENTS
# The validator uses regex to find [START], [STEP], [END] in stdout.
# flush=True is REQUIRED so output is not buffered.
# ════════════════════════════════════════════════════════════════════════════════

def log_start(task: str):
    """MANDATORY: printed once at the beginning of each task."""
    print(f"[START] task={task}", flush=True)


def log_step(step: int, reward: float):
    """MANDATORY: printed after every single step (email processed)."""
    print(f"[STEP] step={step} reward={reward:.4f}", flush=True)


def log_end(task: str, score: float, steps: int):
    """MANDATORY: printed once at the end of each task."""
    print(f"[END] task={task} score={score:.4f} steps={steps}", flush=True)


# ════════════════════════════════════════════════════════════════════════════════
# LLM SETUP
# ════════════════════════════════════════════════════════════════════════════════

def make_llm_client() -> OpenAI:
    return OpenAI(
        base_url=API_BASE_URL,
        api_key=HF_TOKEN if HF_TOKEN else "dummy",
    )


def call_llm(client: OpenAI, system_prompt: str, user_prompt: str, max_tokens: int = 300) -> str:
    """Call the LLM. Returns response text. Falls back to empty string on error."""
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=max_tokens,
            stream=False,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print(f"[DEBUG] LLM error: {e}", file=sys.stderr, flush=True)
        return ""


# ════════════════════════════════════════════════════════════════════════════════
# TASK-SPECIFIC PROMPTS & ACTION BUILDERS
# ════════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an expert email triage assistant.
Follow the task instructions exactly. Be precise."""


def build_action_spam(obs: dict, llm_client: OpenAI) -> dict:
    """Classify email as spam or not_spam."""
    email_body = obs.get("body", obs.get("email_text", obs.get("observation", "")))
    subject    = obs.get("subject", "")
    sender     = obs.get("sender", "")

    user_prompt = f"""Classify this email as EXACTLY 'spam' or 'not_spam'.
Reply with ONE WORD only.

From: {sender}
Subject: {subject}
Body: {email_body}

Classification:"""

    result = call_llm(llm_client, SYSTEM_PROMPT, user_prompt, max_tokens=10).lower()

    if "not_spam" in result or "not spam" in result:
        category = "not_spam"
    elif "spam" in result:
        category = "spam"
    else:
        category = "not_spam"

    return {"category": category}


def build_action_urgency(obs: dict, llm_client: OpenAI) -> dict:
    """Detect email urgency: low / medium / high."""
    email_body = obs.get("body", obs.get("email_text", obs.get("observation", "")))
    subject    = obs.get("subject", "")
    sender     = obs.get("sender", "")

    user_prompt = f"""Rate the urgency of this email as EXACTLY 'low', 'medium', or 'high'.
Reply with ONE WORD only.

From: {sender}
Subject: {subject}
Body: {email_body}

Urgency:"""

    result = call_llm(llm_client, SYSTEM_PROMPT, user_prompt, max_tokens=10).lower()

    if "high" in result or "critical" in result:
        urgency = "high"
    elif "medium" in result or "med" in result or "moderate" in result:
        urgency = "medium"
    else:
        urgency = "low"

    return {"urgency": urgency}


def build_action_reply(obs: dict, llm_client: OpenAI) -> dict:
    """Write a professional reply of 50-200 words."""
    email_body = obs.get("body", obs.get("email_text", obs.get("observation", "")))
    subject    = obs.get("subject", "")
    sender     = obs.get("sender", "the sender")

    user_prompt = f"""Write a professional, polite email reply of 50-200 words.
Address the sender's request directly. Do NOT use placeholders like [Your Name].

From: {sender}
Subject: {subject}
Body: {email_body}

Reply:"""

    reply = call_llm(llm_client, SYSTEM_PROMPT, user_prompt, max_tokens=250)

    if not reply or len(reply.split()) < 20:
        reply = (
            f"Dear {sender}, thank you for reaching out. "
            "We have received your message and are currently reviewing your request. "
            "Our team will respond with a full update within one business day. "
            "Please do not hesitate to contact us if you have any further questions. "
            "We appreciate your patience and look forward to assisting you further."
        )

    return {"reply_text": reply}


ACTION_BUILDERS = {
    "spam_classification": build_action_spam,
    "urgency_detection":   build_action_urgency,
    "professional_reply":  build_action_reply,
}


# ════════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT HTTP CALLS
# ════════════════════════════════════════════════════════════════════════════════

async def env_health(http: httpx.AsyncClient) -> bool:
    try:
        r = await http.get(f"{ENV_BASE_URL}/health", timeout=15)
        return r.status_code == 200
    except Exception as e:
        print(f"[DEBUG] Health check failed: {e}", file=sys.stderr, flush=True)
        return False


async def env_reset(http: httpx.AsyncClient, task_name: str) -> dict:
    """POST /reset with task name in JSON body."""
    r = await http.post(
        f"{ENV_BASE_URL}/reset",
        json={"task_name": task_name},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


async def env_step(http: httpx.AsyncClient, action: dict) -> dict:
    """POST /step with action dict as JSON body."""
    r = await http.post(
        f"{ENV_BASE_URL}/step",
        json=action,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


# ════════════════════════════════════════════════════════════════════════════════
# EPISODE RUNNER
# ════════════════════════════════════════════════════════════════════════════════

async def run_task(task_name: str, llm_client: OpenAI, http: httpx.AsyncClient) -> float:
    """
    Runs one full episode for a task.
    Prints [START], [STEP]s, [END] to stdout.
    Returns final normalised score in [0.0, 1.0].
    """
    # ── MANDATORY: print START ────────────────────────────────
    log_start(task_name)

    rewards    = []
    steps_done = 0
    score      = 0.0

    try:
        # ── Reset environment ─────────────────────────────────
        reset_data = await env_reset(http, task_name)

        if "observation" in reset_data:
            obs = reset_data["observation"]
        else:
            obs = reset_data

        done = reset_data.get("done", False)

        builder = ACTION_BUILDERS.get(task_name)
        if builder is None:
            print(f"[DEBUG] Unknown task: {task_name}", file=sys.stderr, flush=True)
            log_step(1, 0.0)
            log_end(task_name, score=0.0, steps=1)
            return 0.0

        # ── Step loop ─────────────────────────────────────────
        for step_num in range(1, MAX_STEPS + 1):
            if done:
                break

            action = builder(obs, llm_client)
            print(f"[DEBUG] step={step_num} action_keys={list(action.keys())}", file=sys.stderr, flush=True)

            step_data = await env_step(http, action)

            reward   = float(step_data.get("reward", 0.0))
            done     = step_data.get("done", True)
            next_obs = step_data.get("observation", obs)

            if isinstance(next_obs, dict) and next_obs:
                obs = next_obs

            rewards.append(reward)
            steps_done = step_num

            # ── MANDATORY: print STEP ─────────────────────────
            log_step(step_num, reward)

            if done:
                break

        # ── Compute final score ───────────────────────────────
        if rewards:
            raw_score = sum(rewards) / len(rewards)
            score = round(min(max(raw_score, 0.0), 1.0), 4)
        else:
            score = 0.0

    except Exception as e:
        print(f"[DEBUG] Task {task_name} error: {e}", file=sys.stderr, flush=True)
        # Always emit at least one STEP so validator sees output
        if steps_done == 0:
            steps_done = 1
            log_step(1, 0.0)

    # ── MANDATORY: print END ──────────────────────────────────
    log_end(task_name, score=score, steps=steps_done)
    return score


# ════════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════════

async def amain():
    print(f"[DEBUG] ENV_URL={ENV_BASE_URL} MODEL={MODEL_NAME}", file=sys.stderr, flush=True)

    llm_client = make_llm_client()

    async with httpx.AsyncClient(timeout=60.0) as http:

        healthy = await env_health(http)
        if not healthy:
            print(f"[DEBUG] Warning: health check failed, proceeding anyway", file=sys.stderr, flush=True)

        all_scores = {}
        for task in TASKS_TO_RUN:
            print(f"[DEBUG] Starting task: {task}", file=sys.stderr, flush=True)
            score = await run_task(task, llm_client, http)
            all_scores[task] = score

    overall = sum(all_scores.values()) / len(all_scores) if all_scores else 0.0
    print(f"[DEBUG] OVERALL={overall:.4f}", file=sys.stderr, flush=True)


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()
