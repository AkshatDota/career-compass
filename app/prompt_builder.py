from app.questions import ALL_QUESTIONS_BY_ID, _parse_answer

_PRONOUNS = {
    "male":   {"subject": "he",   "object": "him",  "possessive": "his"},
    "female": {"subject": "she",  "object": "her",  "possessive": "her"},
    "other":  {"subject": "they", "object": "them", "possessive": "their"},
}


def _build_system_prompt(name: str, gender: str) -> str:
    p = _PRONOUNS.get(gender, _PRONOUNS["other"])
    name_clause = (
        f"The student's name is {name}. "
        f"Address {p['object']} by name throughout your response — "
        f"in taglines, why_it_fits, and the summary. "
        f"Use the pronouns {p['subject']}/{p['object']}/{p['possessive']} when referring to {name}. "
    ) if name else (
        "Address the student warmly throughout your response. "
    )
    return (
        "You are an expert career counsellor specialising in guiding Indian students "
        "who have completed or are pursuing a Bachelor's in Computer Applications (BCA). "
        + name_clause +
        "You have deep knowledge of the Indian job market, salary ranges (in INR LPA), "
        "and career growth trajectories across the private sector, government sector, and entrepreneurship. "
        "You are warm, encouraging, and specific. "
        "Always give practical, actionable advice grounded in today's reality."
    )

_RESPONSE_SCHEMA = """
{
  "careers": [
    {
      "title": "Career title",
      "match_score": 85,
      "tagline": "One sentence — why this suits her specifically",
      "why_it_fits": "2-3 sentences connecting her answers to this career",
      "salary": {
        "fresher": "₹X – ₹Y LPA",
        "mid_level": "₹X – ₹Y LPA (3–5 years)",
        "senior": "₹X – ₹Y LPA (10+ years)"
      },
      "skills_to_build": ["skill1", "skill2", "skill3", "skill4"],
      "roadmap": [
        "Step 1: ...",
        "Step 2: ...",
        "Step 3: ...",
        "Step 4: ..."
      ],
      "top_companies": ["Indian Company A", "Indian Company B", "Indian Company C"]
    }
  ],
  "summary": "A warm 2-3 sentence closing note addressing her directly, encouraging her and highlighting her strongest trait from her answers"
}
"""


def _format_answer(answer_raw: str) -> str:
    parts = [p for p in _parse_answer(answer_raw) if p]
    if not parts:
        return "(no answer)"
    return ", ".join(parts) if len(parts) > 1 else parts[0]


def build_prompt(answers: list[dict]) -> tuple[str, str]:
    """
    Build (system_prompt, user_prompt) for the AI call.

    Pulls name and gender from special user_name / user_gender answer rows,
    builds a dynamic system prompt with correct pronouns, then formats the
    remaining Q&A answers for the user prompt.
    """
    name   = ""
    gender = ""
    qa_rows: list[dict] = []

    for row in answers:
        qid = row["question_id"]
        if qid == "user_name":
            name = _format_answer(row["answer"]).strip()
        elif qid == "user_gender":
            gender = _format_answer(row["answer"]).strip()
        else:
            qa_rows.append(row)

    system_prompt = _build_system_prompt(name, gender)
    name_ref = name or "the student"

    lines: list[str] = []
    for row in qa_rows:
        qid = row["question_id"]
        stored_qt = row["question_text"] if row["question_text"] else None
        if stored_qt:
            question_text = stored_qt
        else:
            q = ALL_QUESTIONS_BY_ID.get(qid)
            question_text = q["text"] if q else qid

        answer_text = _format_answer(row["answer"])
        lines.append(f"Q: {question_text}\nA: {answer_text}")

    formatted_qa = "\n\n".join(lines)

    user_prompt = (
        f"Based on the following answers from {name_ref}, a BCA student, recommend "
        "the top 3-5 most suitable career paths for them.\n\n"
        f"STUDENT'S ANSWERS:\n{formatted_qa}\n\n"
        "CRITICAL RULES — follow every one exactly:\n\n"
        "1. SALARY: Express ALL figures in Indian Rupees as LPA only (e.g. ₹4–7 LPA). Never use USD.\n\n"
        "2. JOB TITLE: Use the exact job title that appears on LinkedIn India / Naukri today "
        "(e.g. 'Software Development Engineer', 'Data Analyst', 'Product Manager', "
        "'Business Analyst', 'UX Designer', 'Content Strategist', 'Civil Services Officer (IAS/IPS)', "
        "'Probationary Officer – Banking (IBPS PO)', 'PSU Engineer (GATE)', 'Chartered Accountant'). "
        "Do NOT invent vague titles that do not exist as active job roles.\n\n"
        "3. COMPANIES: In top_companies, only list companies that ACTIVELY and REGULARLY hire for "
        "that specific role in India RIGHT NOW. "
        "TCS/Infosys/Wipro/HCL for IT services; Amazon/Microsoft/Google/Flipkart/Swiggy/PhonePe/Razorpay "
        "for product engineering; Deloitte/EY/PwC/KPMG for consulting/finance; "
        "UPSC/SSC/IBPS/State PSC for government; HDFC Bank/ICICI Bank/Axis Bank for banking. "
        "Do NOT list companies that do not publish openings for that specific role.\n\n"
        "4. GOVERNMENT / BUSINESS: Where the student's answers suggest stability, social impact, or "
        "non-tech interests, include at least one government-sector or business-sector career path "
        "(Civil Services, Banking, PSU, Management Trainee, CA, etc.).\n\n"
        f"5. match_score: integer 0–100 reflecting how closely this career matches {name_ref}'s specific answers.\n\n"
        f"6. Address {name_ref} by first name in tagline, why_it_fits, and summary.\n\n"
        "Respond with ONLY valid JSON, no preamble, no markdown fences:\n"
        f"{_RESPONSE_SCHEMA}"
    )

    return system_prompt, user_prompt
