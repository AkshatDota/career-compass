import json
from typing import Any

# ── Base question bank ────────────────────────────────────────────────────────

BASE_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "q1",
        "text": "Which broad areas excite you most? (Select all that apply)",
        "type": "multi",
        "options": [
            "Technology",
            "Business",
            "Healthcare",
            "Creative Arts",
            "Education",
            "Law & Policy",
            "Science & Research",
        ],
        "triggers": {},
    },
    {
        "id": "q2",
        "text": "How do you prefer to work?",
        "type": "single",
        "options": [
            "Alone on focused tasks",
            "In a team with collaboration",
            "Mix of both",
            "With clients/people daily",
        ],
        "triggers": {},
    },
    {
        "id": "q3",
        "text": "What matters most to you in a career? (Select all that apply)",
        "type": "multi",
        "options": [
            "High income",
            "Work-life balance",
            "Making social impact",
            "Creative freedom",
            "Job security",
            "Learning & growth",
            "Prestige",
        ],
        "triggers": {},
    },
    {
        "id": "q4",
        "text": "How do you feel about mathematics and logic?",
        "type": "single",
        "options": [
            "Love it — it comes naturally to me",
            "It's okay — I can manage when needed",
            "Prefer to avoid it if possible",
        ],
        "triggers": {},
    },
    {
        "id": "q5",
        "text": "How confident are you in your communication and presentation skills?",
        "type": "single",
        "options": [
            "Very comfortable — I enjoy speaking to groups",
            "Moderate — I can manage in most situations",
            "Prefer written over spoken communication",
            "Low confidence — I find it stressful",
        ],
        "triggers": {},
    },
    {
        "id": "q6",
        "text": "Are you open to studying further after BCA?",
        "type": "single",
        "options": [
            "Yes — Masters or MBA",
            "Yes — short certifications only",
            "No — I want to start working immediately",
            "Undecided",
        ],
        "triggers": {},
    },
    {
        "id": "q7",
        "text": "Where do you see yourself working?",
        "type": "single",
        "options": [
            "MNC (large multinational company)",
            "Startup",
            "Government organisation",
            "My own business",
            "NGO or non-profit",
            "Not sure yet",
        ],
        "triggers": {},
    },
    {
        "id": "q8",
        "text": "How do you handle pressure and deadlines?",
        "type": "single",
        "options": [
            "I thrive under pressure — it motivates me",
            "I prefer a steady, predictable pace",
            "Depends on the type of work",
        ],
        "triggers": {},
    },
]

# ── Adaptive follow-up questions (keyed by interest area from q1) ─────────────

ADAPTIVE_QUESTIONS: dict[str, dict[str, Any]] = {
    "Technology": {
        "id": "q_tech",
        "text": "You selected Technology — which part excites you most?",
        "type": "single",
        "options": [
            "Software development & engineering",
            "Data & AI / Machine learning",
            "Cybersecurity",
            "UI/UX Design & product design",
            "IT Infrastructure & cloud",
        ],
        "triggers": {},
    },
    "Business": {
        "id": "q_biz",
        "text": "You selected Business — which business role appeals to you?",
        "type": "single",
        "options": [
            "Finance & Accounting",
            "Marketing & brand strategy",
            "Operations & supply chain",
            "Consulting & strategy",
            "Entrepreneurship & startups",
        ],
        "triggers": {},
    },
    "Healthcare": {
        "id": "q_health",
        "text": "You selected Healthcare — which direction interests you?",
        "type": "single",
        "options": [
            "Clinical care & patient interaction",
            "Health technology & digital health",
            "Medical research & drug discovery",
            "Public health & policy",
            "Medical devices & biomedical engineering",
        ],
        "triggers": {},
    },
    "Creative Arts": {
        "id": "q_creative",
        "text": "You selected Creative Arts — what is your creative focus?",
        "type": "single",
        "options": [
            "Graphic design & visual communication",
            "Content creation & storytelling",
            "Animation & VFX",
            "Music & audio production",
            "Photography & videography",
        ],
        "triggers": {},
    },
    "Education": {
        "id": "q_edu",
        "text": "You selected Education — what role in education appeals to you?",
        "type": "single",
        "options": [
            "Teaching & classroom instruction",
            "EdTech & e-learning platforms",
            "Curriculum design & academic publishing",
            "Corporate training & L&D",
        ],
        "triggers": {},
    },
    "Law & Policy": {
        "id": "q_law",
        "text": "You selected Law & Policy — which area interests you?",
        "type": "single",
        "options": [
            "Corporate law & legal practice",
            "Civil services & government (IAS/IPS etc.)",
            "Policy research & think tanks",
            "Compliance & regulatory affairs",
        ],
        "triggers": {},
    },
    "Science & Research": {
        "id": "q_sci",
        "text": "You selected Science & Research — which research field draws you?",
        "type": "single",
        "options": [
            "Life sciences & biotechnology",
            "Physics & materials science",
            "Environmental & climate science",
            "Data science & computational research",
            "R&D in industry (FMCG, pharma, tech)",
        ],
        "triggers": {},
    },
}

# Ordered list of interest areas to maintain deterministic sequence ordering
_AREA_ORDER = [
    "Technology",
    "Business",
    "Healthcare",
    "Creative Arts",
    "Education",
    "Law & Policy",
    "Science & Research",
]

# ── Lookup helpers ────────────────────────────────────────────────────────────

_BASE_BY_ID: dict[str, dict] = {q["id"]: q for q in BASE_QUESTIONS}
_ADAPTIVE_BY_ID: dict[str, dict] = {q["id"]: q for q in ADAPTIVE_QUESTIONS.values()}
ALL_QUESTIONS_BY_ID: dict[str, dict] = {**_BASE_BY_ID, **_ADAPTIVE_BY_ID}


def _parse_answer(raw: str) -> list[str]:
    """Return answer as a list regardless of whether it was stored as JSON or plain text."""
    if not raw or not raw.strip():
        return []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(x) for x in parsed if x is not None and str(x).strip()]
        return [str(parsed)] if str(parsed).strip() else []
    except (json.JSONDecodeError, ValueError):
        return [raw] if raw.strip() else []


def get_question_sequence(session_answers: list[dict]) -> list[str]:
    """
    Build the ordered list of question IDs for this session.

    Base order: q1, [adaptive follow-ups for each area selected in q1], q2-q8.
    Adaptive questions are inserted after q1 in the order areas appear in _AREA_ORDER.
    """
    sequence = ["q1"]

    # Find the q1 answer (if already answered) to inject adaptive follow-ups
    q1_answer_raw = next(
        (row["answer"] for row in session_answers if row["question_id"] == "q1"),
        None,
    )

    if q1_answer_raw is not None:
        selected_areas = _parse_answer(q1_answer_raw)
        for area in _AREA_ORDER:
            if area in selected_areas and area in ADAPTIVE_QUESTIONS:
                sequence.append(ADAPTIVE_QUESTIONS[area]["id"])

    # Remaining base questions
    sequence += ["q2", "q3", "q4", "q5", "q6", "q7", "q8"]
    return sequence


def get_next_question(
    session_answers: list[dict],
) -> tuple[dict | None, int, int]:
    """
    Return (next_question_dict, current_position, total_questions).

    next_question_dict is None when all questions have been answered.
    current_position is 1-indexed (i.e. "you are on question N of total").
    """
    answered_ids = {row["question_id"] for row in session_answers}
    sequence = get_question_sequence(session_answers)
    total = len(sequence)

    for idx, qid in enumerate(sequence):
        if qid not in answered_ids:
            question = ALL_QUESTIONS_BY_ID.get(qid)
            if question is None:
                continue
            return question, idx + 1, total

    return None, total, total
