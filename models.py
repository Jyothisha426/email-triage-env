# models.py
# ─────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS:
#   OpenEnv requires *typed* models for every piece of data
#   that flows between the environment and the agent.
#   Pydantic enforces types at runtime, so if the agent sends
#   garbage data, we catch it immediately with a clear error.
# ─────────────────────────────────────────────────────────────

from pydantic import BaseModel
from typing import Optional, List


# ── What the agent SEES (the situation it must respond to) ───
class EmailObservation(BaseModel):
    email_id: str               # unique ID for this email
    subject: str                # email subject line
    body: str                   # email body text
    sender: str                 # who sent it
    task_name: str              # which task the agent is solving
    task_description: str       # plain-English instructions for the agent
    step_number: int            # which step we're on (1-based)


# ── What the agent DOES (its response/action) ────────────────
class EmailAction(BaseModel):
    response: str               # the agent's answer / classification / reply


# ── What we send back after each step ────────────────────────
class StepResult(BaseModel):
    observation: EmailObservation
    reward: float               # 0.0 to 1.0
    done: bool                  # True = episode is over
    info: dict                  # extra debug info (grader feedback etc.)


# ── Current state snapshot ───────────────────────────────────
class EnvState(BaseModel):
    task_name: str
    step_number: int
    total_steps: int
    cumulative_reward: float
    done: bool


# ── Reset response ────────────────────────────────────────────
class ResetResult(BaseModel):
    observation: EmailObservation
    info: dict


# ── Task metadata (for listing available tasks) ──────────────
class TaskInfo(BaseModel):
    name: str
    description: str
    difficulty: str             # easy / medium / hard
    max_steps: int
    max_reward: float
