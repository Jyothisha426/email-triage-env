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
# CRITICAL: The validator injects API_BASE_URL and API_KEY.
# We MUST use os.environ.get("API_KEY") — not HF_TOKEN or any other var.
# Using the wrong key means the LiteLLM proxy never sees our calls → FAIL.
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
API_KEY      = os.environ.get("API_KEY",      "dummy-key-for-local-testing")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "gpt-4o-mini")
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "https://jyothisha426-email-triage-env.hf.space").rstrip("/")

# CHANGE 1: added department_routing
TASKS_TO_RUN = [
    "spam_classification",
    "urgency_detection",
    "professional_reply",
    "department_routing",
]

# CHANGE 2: updated from 6 to 15 to match expanded email list
MAX_STEPS = 15


# ════════════════════════════════════════════════════════════════════════════════
# SCORE SAFETY
# ════════════════════════════════════════════════════════════════════════════════

def safe_score(score: float) -> float:
    return round(min(max(float(score), 0.0001), 0.9999), 4)


def safe_reward(reward: float) -> float:
    return round(min(max(float(reward), 0.0001), 0.9999), 4)


# ════════════════════════════════════════════════════════════════════════════════
# MANDATORY LOGGING
# ════════════════════════════════════════════════════════════════════════════════

def log_start(task: str):
    print(f"[START] task={task}", flush=True)


def log_step(step: int, reward: float):
    r = safe_reward(reward)
    print(f"[STEP] step={step} reward={r}", flush=True)


def log_end(task: str, score: float, steps: int):
    s = safe_score(score)
    print(f"[END] task={task} score={s} steps={steps}", flush=True)


# ════════════════════════════════════════════════════════════════════════════════
# LLM CLIENT — MUST use API_BASE_URL + API_KEY from environment
# ════════════════════════════════════════════════════════════════════════════════

def make_llm_client() -> OpenAI:
    print(f"[DEBUG] LLM client: base_url={API_BASE_URL} model={MODEL_NAME}", file=sys.stderr, flush=True)
    return OpenAI(
        base_url=API_BASE_URL,
        api_key=API_KEY,   # ← MUST be API_KEY, NOT HF_TOKEN
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
# ACTION BUILDERS
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
        cat = "not_spam"
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


# CHANGE 3: new function for department routing task
def build_routing_action(obs: dict, llm: OpenAI) -> dict:
    body    = obs.get("body", obs.get("email_text", obs.get("observation", "")))
    subject = obs.get("subject", "")
    sender  = obs.get("sender", "")
    user = f"""Route this email to the correct department.
Reply with EXACTLY one of: engineering, finance, hr, support, management, spam_filter

Rules:
- engineering: technical issues, outages, bugs, security incidents
- finance: invoices, payments, budgets, expenses
- hr: people, hiring, onboarding, team events, newsletters
- support: customer complaints, order issues, refunds
- management: strategy, partnerships, executive decisions, approvals
- spam_filter: spam, phishing, scam, unsolicited commercial email

From: {sender}
Subject: {subject}
Body: {body}

Department:"""
    raw = call_llm(llm, SYS, user, max_tokens=15).lower().replace("-", "_").replace(" ", "_")
    departments = ["engineering", "finance", "hr", "support", "management", "spam_filter"]
    detected = next((d for d in departments if d in raw), "management")
    return {"response": detected}


# CHANGE 4: registered department_routing in ACTION_BUILDERS
ACTION_BUILDERS = {
    "spam_classification": build_spam_action,
    "urgency_detection":   build_urgency_action,
    "professional_reply":  build_reply_action,
    "department_routing":  build_routing_action,
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
    log_start(task_name)

    rewards    = []
    steps_done = 0
    score      = 0.0001

    try:
        reset_data = await env_reset(http, task_name)
        obs  = reset_data.get("observation", reset_data)
        done = reset_data.get("done", False)

        builder = ACTION_BUILDERS.get(task_name)
        if builder is None:
            log_step(1, 0.0001)
            log_end(task_name, score=0.0001, steps=1)
            return 0.0001

        for step_num in range(1, MAX_STEPS + 1):
            if done:
                break

            action = builder(obs, llm)
            print(f"[DEBUG] step={step_num} action={action}", file=sys.stderr, flush=True)

            step_data  = await env_step(http, action)
            raw_reward = float(step_data.get("reward", 0.0001))
            reward     = safe_reward(raw_reward)
            done       = step_data.get("done", True)

            next_obs = step_data.get("observation", obs)
            if isinstance(next_obs, dict) and next_obs:
                obs = next_obs

            rewards.append(reward)
            steps_done = step_num
            log_step(step_num, reward)

            if done:
                break

        raw_score = sum(rewards) / len(rewards) if rewards else 0.0001
        score     = safe_score(raw_score)

    except Exception as e:
        print(f"[DEBUG] Task {task_name} error: {e}", file=sys.stderr, flush=True)
        if steps_done == 0:
            steps_done = 1
            log_step(1, 0.0001)

    log_end(task_name, score=safe_score(score), steps=max(steps_done, 1))
    return safe_score(score)


# ════════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════════

async def amain():
    print(f"[DEBUG] ENV={ENV_BASE_URL} MODEL={MODEL_NAME} API_BASE={API_BASE_URL}", file=sys.stderr, flush=True)
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
    for task, score in all_scores.items():
        print(f"[DEBUG]   {task}: {score}", file=sys.stderr, flush=True)


def main():
    asyncio.run(amain())


if __name__ == "__main__":
    main()