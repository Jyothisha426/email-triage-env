---
title: Email Triage Environment
emoji: 📧
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# 📧 Email Triage RL Environment

An **OpenEnv-compatible reinforcement learning environment** where an AI agent learns to triage emails across four progressively harder tasks — from simple spam detection to department routing and professional reply writing.

---

## What This Environment Does

Real-world email triage is a high-value automation target. This environment teaches an AI agent four core skills:

| Task                  | Difficulty  | What the agent must do                                     |
| --------------------- | ----------- | ---------------------------------------------------------- |
| `spam_classification` | ⭐ Easy     | Classify each email as `spam` or `not_spam`                |
| `urgency_detection`   | ⭐⭐ Medium | Classify urgency as `low`, `medium`, `high`, or `critical` |
| `department_routing`  | ⭐⭐ Medium | Route email to the right department (6 options)            |
| `professional_reply`  | ⭐⭐⭐ Hard | Write a 50–200 word professional reply                     |

Each task runs over **15 diverse emails** covering spam, outages, invoices, customer complaints, partnerships, and more. Rewards are continuous and strictly between 0 and 1, giving the agent a rich learning signal.

---

## Observation Space

Each step, the agent receives:

```json
{
  "email_id": "email_002",
  "subject": "Production server is DOWN - immediate action needed",
  "body": "Hi team, Our main production database has crashed...",
  "sender": "oncall@ourcompany.com",
  "task_name": "urgency_detection",
  "task_description": "Classify urgency as low / medium / high / critical...",
  "step_number": 3
}
```

## Action Space

The agent sends a single JSON field:

```json
{ "response": "critical" }
```

The response format depends on the task — a label, urgency level, department name, or free-form reply text.

---

## Reward Design

All rewards are strictly between 0 and 1 (never exactly 0.0 or 1.0).

**Task 1 — Spam Classification**
| Outcome | Reward |
|---|---|
| Correct label, exact format | 0.95 |
| Correct intent, slightly malformed | 0.75 |
| Wrong | 0.05 |

**Task 2 — Urgency Detection**
| Outcome | Reward |
|---|---|
| Exact match | 0.95 |
| One level off (e.g. high vs critical) | 0.45 |
| Two levels off | 0.15 |
| Wrong / unparseable | 0.05 |

**Task 3 — Department Routing**
| Outcome | Reward |
|---|---|
| Correct department | 0.95 |
| Adjacent department (partial credit) | 0.40 |
| Wrong | 0.05 |

**Task 4 — Professional Reply** (multi-dimensional)
| Dimension | Max weight |
|---|---|
| Correct length (50–200 words) | 24% |
| Professional tone (detected phrases) | 24% |
| Keyword relevance (topic coverage) | 34% |
| Non-refusal (agent actually replied) | 14% |

---

## API Endpoints

| Method | Endpoint  | Description                                                      |
| ------ | --------- | ---------------------------------------------------------------- |
| `GET`  | `/health` | Health check — returns 200 OK                                    |
| `GET`  | `/tasks`  | List all 4 tasks with metadata                                   |
| `POST` | `/reset`  | Start new episode — body: `{"task_name": "spam_classification"}` |
| `POST` | `/step`   | Submit action, get reward + next observation                     |
| `GET`  | `/state`  | Current episode state                                            |

Interactive docs available at `/docs` when running.

---

## Setup & Running Locally

```bash
# Clone the repo
git clone https://github.com/Jyothisha426/email-triage-env
cd email-triage-env

# Install dependencies
pip install -r requirements.txt

# Start the environment server
uvicorn main:app --host 0.0.0.0 --port 7860
```

In a new terminal, run the inference agent:

```bash
export API_BASE_URL="https://api.openai.com/v1"
export API_KEY="your-api-key"
export MODEL_NAME="gpt-4o-mini"
python inference.py
```

---

## Running with Docker

```bash
docker build -t email-triage-env .
docker run -p 7860:7860 \
  -e API_BASE_URL="https://api.openai.com/v1" \
  -e API_KEY="your-api-key" \
  -e MODEL_NAME="gpt-4o-mini" \
  email-triage-env
```

---

## Environment Variables

| Variable       | Description                                                     |
| -------------- | --------------------------------------------------------------- |
| `API_BASE_URL` | LLM API base URL — injected by the hackathon validator          |
| `API_KEY`      | API key for the LLM proxy — injected by the hackathon validator |
| `MODEL_NAME`   | Model identifier (e.g. `gpt-4o-mini`)                           |
| `ENV_BASE_URL` | Environment server URL (default: HF Space URL)                  |

> ⚠️ The validator injects `API_BASE_URL` and `API_KEY` at runtime. Do not hardcode keys.

---

## Example Session

```bash
# Start a spam classification episode
curl -X POST "http://localhost:7860/reset" \
  -H "Content-Type: application/json" \
  -d '{"task_name": "spam_classification"}'

# Submit a classification
curl -X POST "http://localhost:7860/step" \
  -H "Content-Type: application/json" \
  -d '{"response": "spam"}'

# Check current state
curl "http://localhost:7860/state"
```

---

## Structured Output (inference.py)

The inference script runs all 4 tasks sequentially and prints structured logs to stdout:

```
[START] task=spam_classification
[STEP] step=1 reward=0.9500
[STEP] step=2 reward=0.9500
...
[END] task=spam_classification score=0.8923 steps=15
[START] task=urgency_detection
...
[END] task=department_routing score=0.7841 steps=15
```

A score ≥ 0.7 per task is considered strong performance.

---

## Project Structure

```
email-triage-env/
├── main.py          # FastAPI server — /reset, /step, /state, /health, /tasks
├── tasks.py         # 15 emails + graders for all 4 tasks
├── models.py        # Pydantic schemas for requests and responses
├── inference.py     # Agent — connects to env and runs all 4 tasks
├── server/
│   ├── app.py       # Entry point for multi-mode deployment (main function)
│   └── __init__.py
├── Dockerfile       # Container definition
├── openenv.yaml     # OpenEnv registration config
└── pyproject.toml   # Package metadata + entry points
```

---

## Built For

**Meta PyTorch Hackathon × Scaler School of Technology**
OpenEnv RL Environment Track — Round 1, April 2026
