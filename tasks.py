# tasks.py
# ─────────────────────────────────────────────────────────────
# SCORES MUST BE STRICTLY BETWEEN 0 AND 1.
# Never return exactly 0.0 or exactly 1.0.
# Safe range: 0.0001 (worst) to 0.9999 (best)
# ─────────────────────────────────────────────────────────────

import re
from typing import Tuple


# ════════════════════════════════════════════════════════════
# SAMPLE EMAILS
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
# SCORE SAFETY HELPER
# ALWAYS call _strict() on every score before returning.
# This guarantees scores are NEVER exactly 0.0 or 1.0.
# ════════════════════════════════════════════════════════════

def _strict(score: float) -> float:
    """
    Clamp score to strictly between 0 and 1.
    Safe range: [0.0001, 0.9999]
    NEVER returns 0.0 or 1.0.
    """
    return round(min(max(float(score), 0.0001), 0.9999), 4)


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
    raw        = agent_response.strip().lower()
    normalized = re.sub(r"[^a-z_]", "", raw.replace(" ", "_"))
    correct    = email["label_spam"]

    if normalized == "not_spam" and correct == "not_spam":
        return _strict(0.95), "Correct! This email is 'not_spam'."
    elif normalized == "spam" and correct == "spam":
        return _strict(0.95), "Correct! This email is 'spam'."
    elif "spam" in normalized and "not" not in normalized and correct == "spam":
        return _strict(0.75), "Mostly correct — spam detected but format slightly off."
    elif ("not" in normalized or "not_spam" in normalized) and correct == "not_spam":
        return _strict(0.75), "Mostly correct — not_spam detected but format slightly off."
    else:
        return _strict(0.05), f"Incorrect. The correct answer was '{correct}'."


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
    raw        = agent_response.strip().lower()
    normalized = re.sub(r"[^a-z]", "", raw)
    correct    = email["label_urgency"]

    detected = None
    for level in URGENCY_LEVELS:
        if level in normalized:
            detected = level
            break

    if detected is None:
        return _strict(0.05), f"Could not parse urgency. Expected: {URGENCY_LEVELS}. Got: '{agent_response[:50]}'"

    if detected == correct:
        return _strict(0.95), f"Correct! Urgency is '{correct}'."

    correct_idx  = URGENCY_LEVELS.index(correct)
    detected_idx = URGENCY_LEVELS.index(detected)

    if abs(correct_idx - detected_idx) == 1:
        return _strict(0.45), f"Close! Correct='{correct}', got='{detected}'. One level off."

    return _strict(0.05), f"Incorrect. Correct urgency='{correct}', got='{detected}'."


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
    Multi-dimensional grader.
    Max possible raw score = 0.24 + 0.24 + 0.34 + 0.14 = 0.96
    (deliberately kept below 1.0 so _strict never has to cap it)
    Score is ALWAYS passed through _strict() before returning.
    """
    text       = agent_response.strip()
    word_count = len(text.split())
    text_lower = text.lower()
    feedback   = []
    score      = 0.0

    # ── Dimension 1: Length (24% max) ────────────────────────
    if 50 <= word_count <= 200:
        score += 0.24
        feedback.append(f"Good length ({word_count} words).")
    elif word_count < 10:
        score += 0.0
        feedback.append(f"Too short ({word_count} words).")
    elif word_count < 50:
        score += 0.08
        feedback.append(f"Short ({word_count} words). Aim for 50-200.")
    else:
        score += 0.12
        feedback.append(f"Long ({word_count} words). Keep under 200.")

    # ── Dimension 2: Professional tone (24% max) ─────────────
    pro_phrases = [
        "thank you", "please", "regards", "sincerely", "i will",
        "we will", "looking forward", "let me know", "happy to",
        "appreciate", "understand", "confirm", "assist",
    ]
    hits = sum(1 for p in pro_phrases if p in text_lower)
    if hits >= 3:
        score += 0.24
        feedback.append("Professional tone detected.")
    elif hits >= 1:
        score += 0.12
        feedback.append("Some professional language used.")
    else:
        feedback.append("Lacks professional tone.")

    # ── Dimension 3: Keyword relevance (34% max) ─────────────
    keywords = email.get("ideal_reply_keywords", [])
    if keywords:
        kw_hits  = sum(1 for kw in keywords if kw.lower() in text_lower)
        kw_ratio = kw_hits / len(keywords)
        score   += round(kw_ratio * 0.34, 4)
        feedback.append(f"Keywords: {kw_hits}/{len(keywords)} addressed.")

    # ── Dimension 4: Not a refusal (14% max) ─────────────────
    refusals = ["i cannot", "i can't", "as an ai", "i'm unable", "i am unable"]
    if not any(r in text_lower for r in refusals):
        score += 0.14
        feedback.append("Reply attempted.")
    else:
        feedback.append("Agent refused to reply.")

    # ── ALWAYS clamp through _strict before returning ─────────
    # Max theoretical score = 0.24+0.24+0.34+0.14 = 0.96 < 1.0
    # But we still call _strict() as a safety net
    return _strict(score), " | ".join(feedback)


# ════════════════════════════════════════════════════════════
# TASK REGISTRY
# ════════════════════════════════════════════════════════════

TASKS = {
    "spam_classification": {
        "info":   TASK1_INFO,
        "grader": grade_spam,
    },
    "urgency_detection": {
        "info":   TASK2_INFO,
        "grader": grade_urgency,
    },
    "professional_reply": {
        "info":   TASK3_INFO,
        "grader": grade_reply,
    },
}