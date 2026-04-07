#!/usr/bin/env python3
"""
inference.py — Email Triage Environment Agent
MANDATORY LOG FORMAT:
  [START] task=TASKNAME
  [STEP] step=N reward=R.RRRR
  [END] task=TASKNAME score=S.SSSS steps=N

Score must be STRICTLY between 0 and 1 (not 0.0, not 1.0).
"""

import os
import sys
import asyncio
import httpx
from openai import OpenAI

# ── Config from environment variables ─────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api-inference.huggingface.co/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "mistralai/Mistral-7B-Instruct-v0.3")
HF_TOKEN     = os.environ.get("HF_TOKEN",     "")
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "https://jyothisha426-email-triage-env.hf.space")

TASKS_TO_RUN = [
    "spam_classification",
    "urgency_detection",
    "professional_reply",
]

MAX_STEPS = 6


# ════════════════════════════════════════════════════════════════════════════════
# SCORE SAFETY — always call this before printing any score
# Ensures score is STRICTLY between 0 and 1 (never 0.0, never 1.0)
# ════════════════════════════════════════════════════════════════════════════════

def safe_score(score: float) -> float:
    """Clamp score to strictly (0, 1): min=0.0001, max=0.9999."""
    clamped = min(max(float(score), 0.0001), 0.9999)
    return round(clamped, 4)


def safe_reward(reward: float) -> float:
    """Clamp reward to strictly (0, 1): min=0.0001, max=0.9999."""
    clamped = min(max(float(reward), 0.0001), 0.9999)
    return round(clamped, 4)


# ════════════════════════════════════════════════════════════════════════════════
# MANDATORY LOGGING — DO NOT CHANGE PRINT FORMAT
# flush=True is required — without it validator may not see output
# ════════════════════════════════════════════════════════════════════════════════

def log_start(task: str):
    print(f"[START] task={task}", flush=True)


def log_step(step: int, reward: float):
    # reward MUST be strictly between 0 and 1
    r = safe_reward(reward)
    print(f"[STEP] step={step} reward={r}", flush=True)


def log_end(task: str, score: float, steps: int):
    # score MUST be strictly between 0 and 1
    s = safe_score(score)
    print(f"[END] task={task} score={s} steps={steps}", flush=True)


# ════════════════════════════════════════════════════════════════════════════════
# LLM CLIENT
# ════════════════════════════════════════════════════════════════════════════════

def make_llm_client() -> OpenAI:
    return OpenAI(
        base_url=API_BASE_URL,
        api_key=HF_TOKEN if HF_TOKEN else "dummy",
    )


def call_llm(client: OpenAI, system: str, user: str, max_tokens: int = 300) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
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
# ACTION BUILDERS — one per task
# ════════════════════════════════════════════════════════════════════════════════

SYS = "You are an expert email triage assistant. Follow instructions exactly. Be precise."


def build_spam_action(obs: dict, llm: OpenAI) -> dict:
    body    = obs.get("body", obs.get("email_text", obs.get("observation", "")))
    subject = obs.get("subject", "")
    sender  = obs.get("sender", "")

    user = f"""Classify this email as EXACTLY 'spam' or 'not_spam'. ONE WORD ONLY.

From: {sender}
Subject: {subject}
Body: {body}

Classification:"""

    raw = call_llm(llm, SYS, user, max_tokens=10).lower()

    if "not_spam" in raw or "not spam" in raw:
        cat = "not_spam"
    elif "spam" in raw:
        cat = "spam"
    else:
        cat = "not_spam"  # safe default

    return {"response": cat}


def build_urgency_action(obs: dict, llm: OpenAI) -> dict:
    body    = obs.get("body", obs.get("email_text", obs.get("observation", "")))
    subject = obs.get("subject", "")
    sender  = obs.get("sender", "")

    user = f"""Rate the urgency of this email.
Reply with EXACTLY one word: low OR medium OR high OR critical

From: {sender}
Subject: {subject}
Body: {body}

Urgency:"""

    raw = call_llm(llm, SYS, user, max_tokens=10).lower()

    if "critical" in raw:
        level = "critical"
    elif "high" in raw:
        level = "high"
    elif "medium" in raw or "med" in raw:
        level = "medium"
    else:
        level = "low"

    return {"response": level}


def build_reply_action(obs: dict, llm: OpenAI) -> dict:
    body    = obs.get("body", obs.get("email_text", obs.get("observation", "")))
    subject = obs.get("subject", "")
    sender  = obs.get("sender", "the sender")

    user = f"""Write a professional email reply of 50-200 words.
Be polite, address the sender's request. No placeholders like [Your Name].

From: {sender}
Subject: {subject}
Body: {body}

Reply:"""

    reply = call_llm(llm, SYS, user, max_tokens=250)

    if not reply or len(reply.split()) < 20:
        reply = (
            f"Dear {sender}, thank you for your email. "
            "We have received your message and are reviewing your request carefully. "
            "Our team will provide a detailed response within one business day. "
            "Please feel free to reach out if you have any additional questions. "
            "We appreciate your patience and look forward to assisting you."
        )

    return {"response": reply}


ACTION_BUILDERS = {
    "spam_classification": build_spam_action,
    "urgency_detection":   build_urgency_action,
    "professional_reply":  build_reply_action,
}


# ════════════════════════════════════════════════════════════════════════════════
# ENV HTTP CALLS
# ════════════════════════════════════════════════════════════════════════════════

async def env_health(http: httpx.AsyncClient) -> bool:
    try:
        r = await http.get(f"{ENV_BASE_URL}/health", timeout=15)
        return r.status_code == 200
    except Exception as e:
        print(f"[DEBUG] health check failed: {e}", file=sys.stderr, flush=True)
        return False


async def env_reset(http: httpx.AsyncClient, task_name: str) -> dict:
    r = await http.post(
        f"{ENV_BASE_URL}/reset",
        json={"task_name": task_name},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


async def env_step(http: httpx.AsyncClient, action: dict) -> dict:
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

async def run_task(task_name: str, llm: OpenAI, http: httpx.AsyncClient) -> float:
    """Run one full episode. Returns score strictly in (0, 1)."""

    log_start(task_name)

    rewards    = []
    steps_done = 0
    # IMPORTANT: default score is 0.0001 NOT 0.0
    score      = 0.0001

    try:
        reset_data = await env_reset(http, task_name)

        # Handle different response shapes from /reset
        obs  = reset_data.get("observation", reset_data)
        done = reset_data.get("done", False)

        builder = ACTION_BUILDERS.get(task_name)
        if builder is None:
            print(f"[DEBUG] Unknown task: {task_name}", file=sys.stderr, flush=True)
            log_step(1, 0.0001)
            log_end(task_name, score=0.0001, steps=1)
            return 0.0001

        for step_num in range(1, MAX_STEPS + 1):
            if done:
                break

            # Build and send action
            action = builder(obs, llm)
            print(f"[DEBUG] step={step_num} action={action}", file=sys.stderr, flush=True)

            step_data  = await env_step(http, action)
            raw_reward = float(step_data.get("reward", 0.0001))

            # CLAMP reward immediately — never allow 0.0 or 1.0
            reward = safe_reward(raw_reward)
            done   = step_data.get("done", True)

            next_obs = step_data.get("observation", obs)
            if isinstance(next_obs, dict) and next_obs:
                obs = next_obs

            rewards.append(reward)
            steps_done = step_num

            log_step(step_num, reward)

            if done:
                break

        # Compute final score — always safe_score it
        if rewards:
            raw_score = sum(rewards) / len(rewards)
        else:
            raw_score = 0.0001

        score = safe_score(raw_score)

    except Exception as e:
        print(f"[DEBUG] Task {task_name} error: {e}", file=sys.stderr, flush=True)
        # Emit at least one step so validator sees output
        if steps_done == 0:
            steps_done = 1
            log_step(1, 0.0001)
        # score stays at 0.0001 (safe default set above)

    # ALWAYS safe_score before log_end
    log_end(task_name, score=safe_score(score), steps=max(steps_done, 1))
    return safe_score(score)


# ════════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════════

async def amain():
    print(f"[DEBUG] ENV={ENV_BASE_URL} MODEL={MODEL_NAME}", file=sys.stderr, flush=True)
    llm = make_llm_client()

    async with httpx.AsyncClient(timeout=60.0) as http:
        healthy = await env_health(http)
        if not healthy:
            print("[DEBUG] health check failed — proceeding anyway", file=sys.stderr, flush=True)

        all_scores = {}
        for task in TASKS_TO_RUN:
            print(f"[DEBUG] starting {task}", file=sys.stderr, flush=True)
            s = await run_task(task, llm, http)
            all_scores[task] = s

    overall = sum(all_scores.values()) / len(all_scores)
    print(f"[DEBUG] OVERALL={safe_score(overall)}", file=sys.stderr, flush=True)


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()