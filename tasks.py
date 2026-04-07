# tasks.py
# ─────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS:
#   This is the HEART of your environment.
#   Each task gives the agent a different challenge:
#     Task 1 (easy)   - classify spam vs not-spam
#     Task 2 (medium) - detect the correct urgency level
#     Task 3 (hard)   - write a full professional reply
#
#   Each task has a GRADER — a function that scores the agent's
#   response from 0.0 (wrong) to 1.0 (perfect).
#   Partial credit makes the reward signal richer, which helps
#   RL agents learn faster (they're not just getting 0 or 1).
#
#   IMPORTANT: Scores must be STRICTLY between 0 and 1.
#   i.e. never exactly 0.0 or exactly 1.0.
#   Range: 0.01 (worst) to 0.99 (best)
# ─────────────────────────────────────────────────────────────

import re
from typing import Tuple


# ════════════════════════════════════════════════════════════
# SAMPLE EMAILS — the environment serves these to the agent
# ════════════════════════════════════════════════════════════

EMAILS = [
    {
        "email_id": "email_001",
        "subject": "Congratulations! You've won $1,000,000!!!",
        "body": "Dear Winner, You have been selected for our grand prize. Click here to claim your reward NOW. Limited time offer! Act fast!",
        "sender": "prizes@totally-legit-lottery.com",
        "label_spam": "spam",
        "label_urgency": "low",
        "ideal_reply_keywords": ["congratulations", "unfortunately", "scam", "not legitimate", "be careful"],
    },
    {
        "email_id": "email_002",
        "subject": "Production server is DOWN - immediate action needed",
        "body": "Hi team, Our main production database has crashed and we're seeing 100% error rates. Customers cannot access the platform. We need all hands on deck immediately. Please join the incident call.",
        "sender": "oncall@ourcompany.com",
        "label_spam": "not_spam",
        "label_urgency": "critical",
        "ideal_reply_keywords": ["joining", "on my way", "acknowledged", "looking into", "investigating", "will help"],
    },
    {
        "email_id": "email_003",
        "subject": "Team lunch next Friday?",
        "body": "Hey everyone! Thinking of organizing a team lunch next Friday at the new Italian place downtown. Let me know if you're interested and any dietary restrictions. Should be fun!",
        "sender": "priya@ourcompany.com",
        "label_spam": "not_spam",
        "label_urgency": "low",
        "ideal_reply_keywords": ["sounds great", "love to", "looking forward", "count me in", "yes", "interested"],
    },
    {
        "email_id": "email_004",
        "subject": "Invoice #4521 overdue - payment required within 48 hours",
        "body": "Dear Customer, This is a reminder that Invoice #4521 for $2,340 is now 30 days overdue. Please arrange payment within 48 hours to avoid service interruption. Contact us if you have questions.",
        "sender": "billing@vendorco.com",
        "label_spam": "not_spam",
        "label_urgency": "high",
        "ideal_reply_keywords": ["payment", "processing", "apologize", "arrange", "send", "confirm", "will"],
    },
    {
        "email_id": "email_005",
        "subject": "Buy cheap medication online - no prescription needed!",
        "body": "Get all medications without prescription! Best prices online. Viagra, painkillers, antibiotics - all available. Fast discrete shipping worldwide. Order now!",
        "sender": "deals@pharma-bargains.net",
        "label_spam": "spam",
        "label_urgency": "low",
        "ideal_reply_keywords": ["spam", "block", "report", "ignore", "illegitimate", "illegal"],
    },
    {
        "email_id": "email_006",
        "subject": "Q3 report review - feedback needed by Thursday",
        "body": "Hi, I've attached the Q3 performance report draft. Could you please review sections 2 and 4 and send me your feedback before Thursday's board meeting? Your input is important for the final version.",
        "sender": "manager@ourcompany.com",
        "label_spam": "not_spam",
        "label_urgency": "medium",
        "ideal_reply_keywords": ["review", "will", "feedback", "thursday", "sections", "send", "look"],
    },
]


# ════════════════════════════════════════════════════════════
# HELPER — clamp scores to strictly (0, 1)
# ════════════════════════════════════════════════════════════

def _strict(score: float) -> float:
    """Clamp score to strictly between 0 and 1: range [0.01, 0.99]."""
    return round(min(max(score, 0.01), 0.99), 4)


# ════════════════════════════════════════════════════════════
# TASK 1 — SPAM CLASSIFICATION (easy)
# ════════════════════════════════════════════════════════════

TASK1_INFO = {
    "name": "spam_classification",
    "description": (
        "Classify the email as either 'spam' or 'not_spam'. "
        "Respond with ONLY one of these two words: spam OR not_spam. "
        "Nothing else."
    ),
    "difficulty": "easy",
    "max_steps": len(EMAILS),
    "max_reward": float(len(EMAILS)),
}


def grade_spam(agent_response: str, email: dict) -> Tuple[float, str]:
    """
    Returns (reward, feedback_message).
    Scores are strictly between 0 and 1: correct=0.99, wrong=0.01.
    """
    raw = agent_response.strip().lower()
    normalized = re.sub(r"[^a-z_]", "", raw.replace(" ", "_"))

    correct = email["label_spam"]

    if normalized == correct:
        return _strict(0.99), f"Correct! This email is '{correct}'."
    elif normalized == "not_spam" and correct == "not_spam":
        return _strict(0.99), "Correct! This email is 'not_spam'."
    elif normalized != "not_spam" and "spam" in normalized and correct == "spam":
        return _strict(0.80), "Mostly correct — detected as spam but format was slightly off."
    elif ("not" in normalized or "not_spam" in normalized) and correct == "not_spam":
        return _strict(0.80), "Mostly correct — not_spam detected but format was slightly off."
    else:
        return _strict(0.01), f"Incorrect. The correct answer was '{correct}'."


# ════════════════════════════════════════════════════════════
# TASK 2 — URGENCY DETECTION (medium)
# ════════════════════════════════════════════════════════════

TASK2_INFO = {
    "name": "urgency_detection",
    "description": (
        "Classify the urgency of this email as one of: low, medium, high, or critical. "
        "Respond with ONLY one word: low OR medium OR high OR critical. "
        "Use 'critical' for system outages or emergencies requiring immediate response. "
        "Use 'high' for time-sensitive issues (hours). "
        "Use 'medium' for things needed within days. "
        "Use 'low' for non-urgent or informational emails."
    ),
    "difficulty": "medium",
    "max_steps": len(EMAILS),
    "max_reward": float(len(EMAILS)),
}

URGENCY_LEVELS = ["low", "medium", "high", "critical"]


def grade_urgency(agent_response: str, email: dict) -> Tuple[float, str]:
    """
    Partial credit based on how far off the agent is.
    Scores are strictly between 0 and 1.
    """
    raw = agent_response.strip().lower()
    normalized = re.sub(r"[^a-z]", "", raw)

    correct = email["label_urgency"]

    detected = None
    for level in URGENCY_LEVELS:
        if level in normalized:
            detected = level
            break

    if detected is None:
        return _strict(0.01), f"Could not parse urgency level. Expected one of: {URGENCY_LEVELS}. Got: '{agent_response[:50]}'"

    if detected == correct:
        return _strict(0.99), f"Correct! Urgency is '{correct}'."

    correct_idx = URGENCY_LEVELS.index(correct)
    detected_idx = URGENCY_LEVELS.index(detected)
    if abs(correct_idx - detected_idx) == 1:
        return _strict(0.50), f"Close! Correct answer was '{correct}', you said '{detected}'. One level off."

    return _strict(0.01), f"Incorrect. Correct urgency was '{correct}', you said '{detected}'."


# ════════════════════════════════════════════════════════════
# TASK 3 — PROFESSIONAL REPLY WRITING (hard)
# ════════════════════════════════════════════════════════════

TASK3_INFO = {
    "name": "professional_reply",
    "description": (
        "Write a professional email reply to the message. "
        "Your reply should: acknowledge the email, address the main point, "
        "and be written in a professional tone. "
        "Keep it between 50 and 200 words. "
        "Write the reply text directly — no subject line needed."
    ),
    "difficulty": "hard",
    "max_steps": len(EMAILS),
    "max_reward": float(len(EMAILS)),
}


def grade_reply(agent_response: str, email: dict) -> Tuple[float, str]:
    """
    Multi-dimensional grader. Each dimension contributes to final score.
    Score is always strictly between 0 and 1.
    """
    text = agent_response.strip()
    word_count = len(text.split())
    feedback_parts = []
    score = 0.0

    # ── Dimension 1: Length (25% of score) ──────────────────
    if 50 <= word_count <= 200:
        score += 0.25
        feedback_parts.append(f"Good length ({word_count} words).")
    elif word_count < 10:
        feedback_parts.append(f"Too short ({word_count} words). Write a proper reply.")
    elif word_count < 50:
        score += 0.10
        feedback_parts.append(f"A bit short ({word_count} words). Aim for 50-200.")
    else:
        score += 0.15
        feedback_parts.append(f"A bit long ({word_count} words). Keep it under 200.")

    # ── Dimension 2: Professional tone (25% of score) ────────
    professional_phrases = [
        "thank you", "please", "regards", "sincerely", "i will",
        "we will", "looking forward", "let me know", "happy to",
        "appreciate", "understand", "confirm", "assist"
    ]
    text_lower = text.lower()
    prof_hits = sum(1 for p in professional_phrases if p in text_lower)
    if prof_hits >= 3:
        score += 0.25
        feedback_parts.append("Professional tone detected.")
    elif prof_hits >= 1:
        score += 0.15
        feedback_parts.append("Some professional language, but could be more formal.")
    else:
        feedback_parts.append("Lacks professional tone. Use phrases like 'Thank you', 'I will...', etc.")

    # ── Dimension 3: Keyword relevance (35% of score) ────────
    keywords = email.get("ideal_reply_keywords", [])
    keyword_hits = sum(1 for kw in keywords if kw.lower() in text_lower)
    keyword_ratio = keyword_hits / len(keywords) if keywords else 0
    keyword_score = round(keyword_ratio * 0.35, 3)
    score += keyword_score
    feedback_parts.append(f"Keyword relevance: {keyword_hits}/{len(keywords)} key topics addressed.")

    # ── Dimension 4: Not a refusal (15% of score) ─────────────
    refusal_phrases = ["i cannot", "i can't", "as an ai", "i'm unable", "i am unable"]
    if not any(r in text_lower for r in refusal_phrases):
        score += 0.15
        feedback_parts.append("Good — agent actually attempted a reply.")
    else:
        feedback_parts.append("Agent refused to reply — this loses points.")

    # ── Clamp strictly between 0 and 1 ───────────────────────
    score = _strict(score)
    return score, " | ".join(feedback_parts)


# ════════════════════════════════════════════════════════════
# TASK REGISTRY — maps task names to their config + grader
# ════════════════════════════════════════════════════════════

TASKS = {
    "spam_classification": {
        "info": TASK1_INFO,
        "grader": grade_spam,
    },
    "urgency_detection": {
        "info": TASK2_INFO,
        "grader": grade_urgency,
    },
    "professional_reply": {
        "info": TASK3_INFO,
        "grader": grade_reply,
    },
}