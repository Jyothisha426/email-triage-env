#!/usr/bin/env python3
# inference.py
# ─────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS:
#   This is the AGENT — the script that actually plays your
#   environment. The evaluator runs this file and checks:
#     1. It completes without errors
#     2. Stdout has [START], [STEP], [END] in exact format
#     3. It produces scores in 0.0–1.0 range
#     4. It finishes in under 20 minutes
#
#   IMPORTANT: The log format is MANDATORY. Any deviation
#   causes scoring to fail. Do not change [START]/[STEP]/[END].
#
#   The agent uses an LLM (via OpenAI-compatible client) to
#   read each email and produce a response.
# ─────────────────────────────────────────────────────────────

import os
import json
import asyncio
import httpx
import sys
from typing import List
from openai import OpenAI

# ── Configuration — loaded from environment variables ─────────
# The evaluator injects these. You MUST use these exact names.
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME   = os.environ.get("MODEL_NAME",   "gpt-4o-mini")
API_KEY      = os.environ.get("HF_TOKEN",     "your-key-here")

# ── Environment server URL ────────────────────────────────────
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")

# ── Episode settings ──────────────────────────────────────────
TASKS_TO_RUN        = ["spam_classification", "urgency_detection", "professional_reply"]
MAX_STEPS_PER_TASK  = 6      # number of emails per task
MAX_TOTAL_REWARD    = 6.0    # max reward per task (one point per email)
SUCCESS_THRESHOLD   = 0.6    # score >= 0.6 counts as success
TEMPERATURE         = 0.0    # deterministic output for reproducibility


# ════════════════════════════════════════════════════════════
# LOGGING — MANDATORY FORMAT (DO NOT CHANGE FIELD NAMES)
# ════════════════════════════════════════════════════════════

def log_start(task: str, env: str, model: str):
    """Print the [START] log line. Evaluator parses this."""
    print(json.dumps({
        "event": "START",
        "task": task,
        "env": env,
        "model": model,
    }), flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error=None):
    """Print a [STEP] log line. Evaluator parses each step."""
    print(json.dumps({
        "event": "STEP",
        "step": step,
        "action": action[:200],   # truncate long replies for log readability
        "reward": reward,
        "done": done,
        "error": error,
    }), flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    """Print the [END] log line. Evaluator reads final score here."""
    print(json.dumps({
        "event": "END",
        "success": success,
        "steps": steps,
        "score": score,
        "rewards": rewards,
    }), flush=True)


# ════════════════════════════════════════════════════════════
# SYSTEM PROMPT — tells the LLM what it's doing
# ════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an expert email triage assistant.
You will receive emails one at a time and must follow the task instructions exactly.

For spam_classification tasks: respond with ONLY the word 'spam' or 'not_spam'.
For urgency_detection tasks: respond with ONLY one word: 'low', 'medium', 'high', or 'critical'.
For professional_reply tasks: write a professional email reply of 50-200 words.

Always follow the task_description field exactly. Be precise and concise."""


def build_user_prompt(obs: dict) -> str:
    """
    Build the prompt the LLM sees for each step.
    We give it the task instructions + the full email.
    """
    return f"""Task: {obs['task_name']}
Instructions: {obs['task_description']}

--- EMAIL ---
From: {obs['sender']}
Subject: {obs['subject']}

{obs['body']}
--- END EMAIL ---

Your response:"""


# ════════════════════════════════════════════════════════════
# LLM CALL — ask the model what to do
# ════════════════════════════════════════════════════════════

def get_llm_action(client: OpenAI, obs: dict) -> str:
    """
    Call the LLM with the current observation.
    Returns the model's response string.
    Falls back to a safe default if the call fails.
    """
    prompt = build_user_prompt(obs)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=300,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        return text if text else "not_spam"
    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)
        # Safe fallback defaults per task
        task = obs.get("task_name", "")
        if task == "spam_classification":
            return "not_spam"
        elif task == "urgency_detection":
            return "low"
        else:
            return "Thank you for your email. I will review this and get back to you shortly. Best regards."


# ════════════════════════════════════════════════════════════
# ENVIRONMENT CLIENT — talks to our FastAPI server
# ════════════════════════════════════════════════════════════

async def env_reset(client: httpx.AsyncClient, task_name: str) -> dict:
    resp = await client.post(f"{ENV_BASE_URL}/reset", params={"task_name": task_name})
    resp.raise_for_status()
    return resp.json()


async def env_step(client: httpx.AsyncClient, response_text: str) -> dict:
    resp = await client.post(
        f"{ENV_BASE_URL}/step",
        json={"response": response_text},
        headers={"Content-Type": "application/json"},
    )
    resp.raise_for_status()
    return resp.json()


# ════════════════════════════════════════════════════════════
# RUN ONE TASK — full episode loop for a single task
# ════════════════════════════════════════════════════════════

async def run_task(task_name: str, llm_client: OpenAI, http_client: httpx.AsyncClient):
    """
    Runs a complete episode:
      reset → loop(step) → log results
    Returns the normalized score [0.0, 1.0].
    """
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env="email-triage-env", model=MODEL_NAME)

    try:
        # ── Reset: get first email ────────────────────────────
        reset_data = await env_reset(http_client, task_name)
        obs = reset_data["observation"]
        done = False

        for step in range(1, MAX_STEPS_PER_TASK + 1):
            if done:
                break

            # ── Agent decides what to do ──────────────────────
            action_text = get_llm_action(llm_client, obs)

            # ── Environment processes the action ─────────────
            step_data = await env_step(http_client, action_text)

            reward = step_data.get("reward", 0.0)
            done   = step_data.get("done", False)
            obs    = step_data.get("observation", obs)

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_text, reward=reward, done=done, error=None)

            if done:
                break

        # ── Compute normalized score ──────────────────────────
        score = sum(rewards) / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD > 0 else 0.0
        score = round(min(max(score, 0.0), 1.0), 4)
        success = score >= SUCCESS_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Task '{task_name}' failed with error: {exc}", flush=True)
        log_step(step=steps_taken + 1, action="ERROR", reward=0.0, done=True, error=str(exc))

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


# ════════════════════════════════════════════════════════════
# MAIN — run all 3 tasks
# ════════════════════════════════════════════════════════════

async def main():
    llm_client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    # Use a single HTTP session for all env calls
    async with httpx.AsyncClient(timeout=60.0) as http_client:

        # Verify environment is running
        try:
            health = await http_client.get(f"{ENV_BASE_URL}/health")
            health.raise_for_status()
            print(f"[DEBUG] Environment healthy: {health.json()}", flush=True)
        except Exception as e:
            print(f"[ERROR] Cannot reach environment at {ENV_BASE_URL}: {e}", flush=True)
            sys.exit(1)

        # Run all 3 tasks and collect scores
        all_scores = {}
        for task_name in TASKS_TO_RUN:
            print(f"\n[DEBUG] ===== Starting task: {task_name} =====", flush=True)
            score = await run_task(task_name, llm_client, http_client)
            all_scores[task_name] = score
            print(f"[DEBUG] Task '{task_name}' final score: {score:.4f}", flush=True)

        # Print summary
        overall = sum(all_scores.values()) / len(all_scores)
        print(f"\n[DEBUG] ===== ALL TASKS COMPLETE =====", flush=True)
        for task, score in all_scores.items():
            print(f"[DEBUG]   {task}: {score:.4f}", flush=True)
        print(f"[DEBUG]   OVERALL AVERAGE: {overall:.4f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
