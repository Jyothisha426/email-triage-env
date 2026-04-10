# tasks.py
# ─────────────────────────────────────────────────────────────
# SCORES MUST BE STRICTLY BETWEEN 0 AND 1.
# Never return exactly 0.0 or exactly 1.0.
# Safe range: 0.0001 (worst) to 0.9999 (best)
# ─────────────────────────────────────────────────────────────

import re
from typing import Tuple


# ════════════════════════════════════════════════════════════
# SAMPLE EMAILS — 15 diverse emails covering all task types
# ════════════════════════════════════════════════════════════

EMAILS = [
    {
        "email_id": "email_001",
        "subject": "Congratulations! You've won $1,000,000!!!",
        "body": "Dear Winner, You have been selected for our grand prize. Click here to claim your reward NOW. Limited time offer! Act fast!",
        "sender": "prizes@totally-legit-lottery.com",
        "label_spam": "spam",
        "label_urgency": "low",
        "label_department": "spam_filter",
        "ideal_reply_keywords": ["unfortunately", "scam", "not legitimate", "be careful", "suspicious"],
    },
    {
        "email_id": "email_002",
        "subject": "Production server is DOWN - immediate action needed",
        "body": "Hi team, Our main production database has crashed and we're seeing 100% error rates. Customers cannot access the platform. We need all hands on deck immediately. Please join the incident call.",
        "sender": "oncall@ourcompany.com",
        "label_spam": "not_spam",
        "label_urgency": "critical",
        "label_department": "engineering",
        "ideal_reply_keywords": ["joining", "acknowledged", "investigating", "will help", "on it"],
    },
    {
        "email_id": "email_003",
        "subject": "Team lunch next Friday?",
        "body": "Hey everyone! Thinking of organizing a team lunch next Friday at the new Italian place downtown. Let me know if you're interested and any dietary restrictions. Should be fun!",
        "sender": "priya@ourcompany.com",
        "label_spam": "not_spam",
        "label_urgency": "low",
        "label_department": "hr",
        "ideal_reply_keywords": ["sounds great", "love to", "looking forward", "count me in", "interested"],
    },
    {
        "email_id": "email_004",
        "subject": "Invoice #4521 overdue - payment required within 48 hours",
        "body": "Dear Customer, This is a reminder that Invoice #4521 for $2,340 is now 30 days overdue. Please arrange payment within 48 hours to avoid service interruption. Contact us if you have questions.",
        "sender": "billing@vendorco.com",
        "label_spam": "not_spam",
        "label_urgency": "high",
        "label_department": "finance",
        "ideal_reply_keywords": ["payment", "processing", "apologize", "arrange", "confirm", "will"],
    },
    {
        "email_id": "email_005",
        "subject": "Buy cheap medication online - no prescription needed!",
        "body": "Get all medications without prescription! Best prices online. Viagra, painkillers, antibiotics - all available. Fast discrete shipping worldwide. Order now!",
        "sender": "deals@pharma-bargains.net",
        "label_spam": "spam",
        "label_urgency": "low",
        "label_department": "spam_filter",
        "ideal_reply_keywords": ["spam", "block", "report", "ignore", "illegitimate"],
    },
    {
        "email_id": "email_006",
        "subject": "Q3 report review - feedback needed by Thursday",
        "body": "Hi, I've attached the Q3 performance report draft. Could you please review sections 2 and 4 and send me your feedback before Thursday's board meeting? Your input is important for the final version.",
        "sender": "manager@ourcompany.com",
        "label_spam": "not_spam",
        "label_urgency": "medium",
        "label_department": "management",
        "ideal_reply_keywords": ["review", "will", "feedback", "thursday", "sections", "look"],
    },
    {
        "email_id": "email_007",
        "subject": "Security breach detected — your account was accessed",
        "body": "We detected a sign-in to your account from an unrecognized device in Romania. If this was not you, please reset your password immediately and contact our security team.",
        "sender": "security@ourcompany.com",
        "label_spam": "not_spam",
        "label_urgency": "critical",
        "label_department": "engineering",
        "ideal_reply_keywords": ["resetting", "immediately", "contacting", "secure", "investigating", "password"],
    },
    {
        "email_id": "email_008",
        "subject": "Your free iPhone 15 is waiting — claim now!",
        "body": "You've been pre-selected for a FREE iPhone 15 Pro! Just complete a short survey and pay $4.99 shipping. This offer expires in 24 hours. Click the link below to claim.",
        "sender": "gifts@prize-central99.com",
        "label_spam": "spam",
        "label_urgency": "low",
        "label_department": "spam_filter",
        "ideal_reply_keywords": ["spam", "phishing", "suspicious", "not legitimate", "ignore"],
    },
    {
        "email_id": "email_009",
        "subject": "New hire onboarding — please complete forms by Monday",
        "body": "Welcome to the team! Please complete your onboarding paperwork including tax forms, direct deposit setup, and equipment preferences by Monday. Log in to the HR portal to get started. Let me know if you have any questions.",
        "sender": "hr@ourcompany.com",
        "label_spam": "not_spam",
        "label_urgency": "medium",
        "label_department": "hr",
        "ideal_reply_keywords": ["complete", "monday", "forms", "thank you", "will", "portal"],
    },
    {
        "email_id": "email_010",
        "subject": "Customer complaint — order #8821 not delivered after 3 weeks",
        "body": "I placed order #8821 three weeks ago and still haven't received it. I've emailed twice with no response. This is completely unacceptable. I want a refund or my order delivered TODAY.",
        "sender": "angry.customer@gmail.com",
        "label_spam": "not_spam",
        "label_urgency": "high",
        "label_department": "support",
        "ideal_reply_keywords": ["apologize", "sorry", "investigate", "refund", "resolve", "immediately", "order"],
    },
    {
        "email_id": "email_011",
        "subject": "Crypto investment opportunity — 500% returns guaranteed",
        "body": "Our proprietary AI trading bot guarantees 500% returns in 30 days. Minimum investment $500. Only 10 spots left. Wire transfer only. Join thousands of satisfied investors today!",
        "sender": "invest@cryptobot-elite.xyz",
        "label_spam": "spam",
        "label_urgency": "low",
        "label_department": "spam_filter",
        "ideal_reply_keywords": ["scam", "fraud", "spam", "not legitimate", "report", "block"],
    },
    {
        "email_id": "email_012",
        "subject": "Partnership proposal — integration with our platform",
        "body": "Hi, I'm the CTO of TechStartup Inc. We have 50,000 users and believe an integration with your platform could benefit both our companies. Would you be open to a 30-minute call next week to explore this?",
        "sender": "cto@techstartup.io",
        "label_spam": "not_spam",
        "label_urgency": "low",
        "label_department": "management",
        "ideal_reply_keywords": ["interested", "happy to", "schedule", "call", "explore", "thank you", "discuss"],
    },
    {
        "email_id": "email_013",
        "subject": "URGENT: Office network is down — no one can work",
        "body": "The entire office network has been down for 2 hours. No one can access internal tools, email, or the internet. IT has been unreachable. We have a client presentation in 3 hours and nothing is working.",
        "sender": "ops@ourcompany.com",
        "label_spam": "not_spam",
        "label_urgency": "critical",
        "label_department": "engineering",
        "ideal_reply_keywords": ["on it", "investigating", "immediately", "escalating", "fix", "working on"],
    },
    {
        "email_id": "email_014",
        "subject": "Monthly team newsletter — August edition",
        "body": "Hi all, Here's the August team newsletter! Highlights: 3 new hires joined engineering, our NPS score hit an all-time high of 72, and the company picnic is scheduled for September 14th. See you there!",
        "sender": "comms@ourcompany.com",
        "label_spam": "not_spam",
        "label_urgency": "low",
        "label_department": "hr",
        "ideal_reply_keywords": ["great", "thank you", "congratulations", "looking forward", "exciting", "news"],
    },
    {
        "email_id": "email_015",
        "subject": "Budget approval needed for Q4 marketing spend — $45,000",
        "body": "Hi, I need approval for the Q4 marketing budget of $45,000 before the end of this week so we can lock in ad rates. The spend breakdown is attached. Please let me know if you have questions or need revisions.",
        "sender": "marketing@ourcompany.com",
        "label_spam": "not_spam",
        "label_urgency": "high",
        "label_department": "finance",
        "ideal_reply_keywords": ["approve", "review", "budget", "questions", "breakdown", "confirm", "will"],
    },
]


# ════════════════════════════════════════════════════════════
# SCORE SAFETY HELPER
# ════════════════════════════════════════════════════════════

def _strict(score: float) -> float:
    """Clamp to strictly (0, 1). NEVER returns 0.0 or 1.0."""
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
    diff = abs(correct_idx - detected_idx)

    if diff == 1:
        return _strict(0.45), f"Close! Correct='{correct}', got='{detected}'. One level off."
    if diff == 2:
        return _strict(0.15), f"Off by two levels. Correct='{correct}', got='{detected}'."

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
    Max possible raw score = 0.24 + 0.24 + 0.34 + 0.14 = 0.96 (safely < 1.0)
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
        "appreciate", "understand", "confirm", "assist", "apologi",
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

    return _strict(score), " | ".join(feedback)


# ════════════════════════════════════════════════════════════
# TASK 4 — DEPARTMENT ROUTING (medium-hard)
# ════════════════════════════════════════════════════════════

TASK4_INFO = {
    "name": "department_routing",
    "description": (
        "Route this email to the correct department. "
        "Respond with ONLY one of: engineering, finance, hr, support, management, spam_filter. "
        "Use 'engineering' for technical issues, outages, security incidents. "
        "Use 'finance' for invoices, payments, budgets, expenses. "
        "Use 'hr' for people, hiring, onboarding, events, newsletters. "
        "Use 'support' for customer complaints, order issues, refunds. "
        "Use 'management' for strategy, partnerships, executive decisions. "
        "Use 'spam_filter' for spam, phishing, scam emails."
    ),
    "difficulty": "medium",
    "max_steps": len(EMAILS),
    "max_reward": float(len(EMAILS)),
}

DEPARTMENTS = ["engineering", "finance", "hr", "support", "management", "spam_filter"]

# Which departments are "close" to each other — partial credit if one level off
DEPT_NEIGHBORS = {
    "engineering": ["management"],
    "finance":     ["management", "support"],
    "hr":          ["management"],
    "support":     ["finance", "management"],
    "management":  ["engineering", "finance", "hr"],
    "spam_filter": [],  # no partial credit for routing spam to real dept
}


def grade_routing(agent_response: str, email: dict) -> Tuple[float, str]:
    raw        = agent_response.strip().lower()
    normalized = re.sub(r"[^a-z_]", "", raw.replace(" ", "_").replace("-", "_"))
    correct    = email.get("label_department", "management")

    detected = None
    for dept in DEPARTMENTS:
        if dept in normalized:
            detected = dept
            break

    if detected is None:
        return _strict(0.05), f"Could not parse department. Expected one of: {DEPARTMENTS}. Got: '{agent_response[:50]}'"

    if detected == correct:
        return _strict(0.95), f"Correct! Routed to '{correct}'."

    if detected in DEPT_NEIGHBORS.get(correct, []):
        return _strict(0.40), f"Partially correct. '{detected}' is close but '{correct}' is better."

    return _strict(0.05), f"Incorrect. Should route to '{correct}', got '{detected}'."


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
    "department_routing": {
        "info":   TASK4_INFO,
        "grader": grade_routing,
    },
}