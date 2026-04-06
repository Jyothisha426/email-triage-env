---
title: Email Triage Environment
emoji: 📧
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# Email Triage Environment

An **OpenEnv-compatible reinforcement learning environment** where an AI agent learns to triage emails across three progressively harder tasks.

---

## What This Environment Does

Real-world email triage is a high-value automation target. This environment teaches an AI agent three core skills:

| Task | Difficulty | What the agent must do |
|---|---|---|
| `spam_classification` | Easy | Classify each email as `spam` or `not_spam` |
| `urgency_detection` | Medium | Classify urgency as `low`, `medium`, `high`, or `critical` |
| `professional_reply` | Hard | Write a 50–200 word professional reply |

Each task runs over 6 emails. Rewards are continuous (0.0–1.0), giving the agent a rich learning signal.

---

## Observation Space

Each step, the agent receives:

```json
{
  "email_id": "email_002",
  "subject": "Production server is DOWN",
  "body": "Hi team, our main database has crashed...",
  "sender": "oncall@ourcompany.com",
  "task_name": "urgency_detection",
  "task_description": "Classify urgency as low / medium / high / critical...",
  "step_number": 3
}
```

## Action Space

The agent sends:

```json
{
  "response": "critical"
}
```

---

## Reward Design

**Task 1 — Spam Classification**
- `1.0` correct label
- `0.8` correct intent but slightly malformed format
- `0.0` wrong

**Task 2 — Urgency Detection**
- `1.0` exact match
- `0.5` one urgency level off (partial credit)
- `0.0` wrong direction

**Task 3 — Professional Reply** (weighted multi-dimensional)
- `0.25` correct length (50–200 words)
- `0.25` professional tone (detected phrases)
- `0.35` keyword relevance (topic coverage)
- `0.15` non-refusal (agent actually replied)

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check — must return 200 |
| GET | `/tasks` | List all 3 tasks with metadata |
| POST | `/reset?task_name=spam_classification` | Start new episode |
| POST | `/step` | Submit action, get reward + next email |
| GET | `/state` | Current episode state |

Interactive docs available at `/docs` when running.

---

## Setup & Running Locally

```bash
# Clone the repo
git clone https://huggingface.co/spaces/YOUR_USERNAME/email-triage-env
cd email-triage-env

# Install dependencies
pip install -r requirements.txt

# Start the environment server
uvicorn main:app --host 0.0.0.0 --port 7860

# In a new terminal, run the inference agent
export API_BASE_URL="https://api.openai.com/v1"
export MODEL_NAME="gpt-4o-mini"
export HF_TOKEN="your-api-key"
python inference.py
```

---

## Running with Docker

```bash
docker build -t email-triage-env .
docker run -p 7860:7860 \
  -e API_BASE_URL="https://api.openai.com/v1" \
  -e MODEL_NAME="gpt-4o-mini" \
  -e HF_TOKEN="your-api-key" \
  email-triage-env
```

---

## Environment Variables (Required)

| Variable | Description |
|---|---|
| `API_BASE_URL` | LLM API endpoint (e.g. `https://api.openai.com/v1`) |
| `MODEL_NAME` | Model identifier (e.g. `gpt-4o-mini`) |
| `HF_TOKEN` | Your Hugging Face / API key |
| `ENV_BASE_URL` | Environment server URL (default: `http://localhost:7860`) |

---

## Example Session

```bash
# Reset to start spam classification
curl -X POST "http://localhost:7860/reset?task_name=spam_classification"

# Submit an action
curl -X POST "http://localhost:7860/step" \
  -H "Content-Type: application/json" \
  -d '{"response": "spam"}'

# Check state
curl "http://localhost:7860/state"
```

---

## Scoring Summary (from inference.py run)

The inference script runs all 3 tasks sequentially and prints:
- Per-step rewards with `[STEP]` log lines
- Final score per task with `[END]` log lines
- Overall average across all tasks

A score ≥ 0.6 per task is considered a success.
