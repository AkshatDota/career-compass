from app.questions import ALL_QUESTIONS_BY_ID, _parse_answer

_PRONOUNS = {
    "male":   {"subject": "he",   "object": "him",  "possessive": "his"},
    "female": {"subject": "she",  "object": "her",  "possessive": "her"},
    "other":  {"subject": "they", "object": "them", "possessive": "their"},
}


def _build_system_prompt(name: str, gender: str, path: str) -> str:
    p = _PRONOUNS.get(gender, _PRONOUNS["other"])
    name_clause = (
        f"The student's name is {name}. "
        f"Address {p['object']} by name throughout your response — "
        f"in taglines, why_it_fits, and the summary. "
        f"Use the pronouns {p['subject']}/{p['object']}/{p['possessive']} when referring to {name}. "
    ) if name else "Address the student warmly throughout your response. "

    if path == "business":
        return (
            "You are an expert startup mentor and business advisor specialising in guiding Indian students "
            "who have completed or are pursuing a Bachelor's in Computer Applications (BCA). "
            + name_clause +
            "You have deep knowledge of the Indian startup ecosystem, bootstrapping, funding options, "
            "investment requirements in INR, realistic revenue expectations for early-stage Indian businesses, "
            "and the practical realities of launching a business in India's Tier-1, Tier-2, and Tier-3 cities. "
            "You are warm, encouraging, and brutally practical. "
            "Always give grounded, actionable advice suited to India's market — not generic Western startup advice."
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


_JOB_RESPONSE_SCHEMA = """
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
  "summary": "A warm 2-3 sentence closing note addressing her directly"
}
"""

_BUSINESS_RESPONSE_SCHEMA = """
{
  "businesses": [
    {
      "title": "Business idea name",
      "match_score": 85,
      "tagline": "One sentence — why this venture suits her specifically",
      "why_it_fits": "2-3 sentences connecting her answers to this business idea",
      "investment": {
        "minimum": "₹X — absolute minimum to get started",
        "comfortable": "₹X — for a stable, proper launch",
        "to_scale": "₹X — to grow meaningfully"
      },
      "revenue_potential": {
        "year1": "₹X – ₹Y LPA (realistic first year)",
        "year3": "₹X – ₹Y LPA (once established)",
        "at_scale": "₹X – ₹Y LPA (at full scale)"
      },
      "skills_to_build": ["skill1", "skill2", "skill3"],
      "roadmap": [
        "Step 1: ...",
        "Step 2: ...",
        "Step 3: ...",
        "Step 4: ..."
      ],
      "resources": ["India-specific platform or resource 1", "Resource 2", "Resource 3"]
    }
  ],
  "summary": "A warm 2-3 sentence closing note addressing her directly, encouraging her entrepreneurial ambition"
}
"""


def _format_answer(answer_raw: str) -> str:
    parts = [p for p in _parse_answer(answer_raw) if p]
    if not parts:
        return "(no answer)"
    return ", ".join(parts) if len(parts) > 1 else parts[0]


def build_prompt(answers: list[dict]) -> tuple[str, str]:
    """Build (system_prompt, user_prompt) for the AI call."""
    name   = ""
    gender = ""
    path   = "job"
    qa_rows: list[dict] = []

    for row in answers:
        qid = row["question_id"]
        if qid == "user_name":
            name = _format_answer(row["answer"]).strip()
        elif qid == "user_gender":
            gender = _format_answer(row["answer"]).strip()
        elif qid == "direction":
            path = _format_answer(row["answer"]).strip().lower()
        else:
            qa_rows.append(row)

    system_prompt = _build_system_prompt(name, gender, path)
    name_ref = name or "the student"

    lines: list[str] = []
    for row in qa_rows:
        qid = row["question_id"]
        stored_qt = row["question_text"] if row["question_text"] else None
        question_text = stored_qt or (ALL_QUESTIONS_BY_ID.get(qid, {}).get("text") or qid)
        answer_text = _format_answer(row["answer"])
        lines.append(f"Q: {question_text}\nA: {answer_text}")

    formatted_qa = "\n\n".join(lines)

    if path == "business":
        user_prompt = (
            f"Based on the following answers from {name_ref}, a BCA student who wants to start a business, "
            "recommend the top 3-4 most suitable business ventures for them.\n\n"
            f"STUDENT'S ANSWERS:\n{formatted_qa}\n\n"
            "CRITICAL RULES — follow every one exactly:\n\n"
            "1. CURRENCY: Express ALL investment and revenue figures in Indian Rupees (₹). "
            "Use LPA for annual revenue (e.g. ₹4–7 LPA). Use lakhs/crores for investment (e.g. ₹50,000 / ₹2 Lakh). Never use USD.\n\n"
            "2. INDIA-SPECIFIC: All advice must be grounded in the Indian market — Indian platforms "
            "(Meesho, Zepto, Zomato, Dunzo, Razorpay, Instamojo, IndiaMART, Flipkart, Amazon.in), "
            "Indian funding options (bootstrapping, family/friends, angel networks like LetsVenture, "
            "government schemes like MSME/Startup India, bank loans under MUDRA), "
            "and Indian regulatory context (GST, MSME registration, FSSAI for food, etc.).\n\n"
            "3. REALISTIC INVESTMENT: The investment_required must be grounded in what it ACTUALLY costs "
            "to launch this business in India today — not theoretical global figures. "
            "Respect the student's stated budget from their answers.\n\n"
            "4. LOCATION-AWARE: Factor in the student's city/location. A business viable in Mumbai "
            "may not be viable in a small town — or may be even MORE viable there with less competition.\n\n"
            f"5. match_score: integer 0–100 reflecting how closely this venture matches {name_ref}'s "
            "specific strengths, investment capacity, location, and interests.\n\n"
            f"6. Address {name_ref} by first name in tagline, why_it_fits, and summary.\n\n"
            "Respond with ONLY valid JSON, no preamble, no markdown fences:\n"
            f"{_BUSINESS_RESPONSE_SCHEMA}"
        )
    else:
        # Detect sector preference to tailor government/private emphasis
        sector_answer = next(
            (_format_answer(r["answer"]) for r in qa_rows if r["question_id"] == "sector"), ""
        ).lower()
        govt_rule = (
            "4. SECTOR FOCUS: The student specifically selected GOVERNMENT / PSU sector. "
            "Prioritise civil services (IAS/IPS/IFS), banking (IBPS PO/SBI PO), PSU engineer (GATE), "
            "SSC/railway roles, and defence. Include at least 2-3 government-track careers."
            if "government" in sector_answer else
            "4. GOVERNMENT / BUSINESS: Where the student's answers suggest stability, social impact, or "
            "non-tech interests, include at least one government-sector or business-sector career path "
            "(Civil Services, Banking, PSU, Management Trainee, CA, etc.)."
        )
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
            f"{govt_rule}\n\n"
            f"5. match_score: integer 0–100 reflecting how closely this career matches {name_ref}'s specific answers.\n\n"
            f"6. Address {name_ref} by first name in tagline, why_it_fits, and summary.\n\n"
            "Respond with ONLY valid JSON, no preamble, no markdown fences:\n"
            f"{_JOB_RESPONSE_SCHEMA}"
        )

    return system_prompt, user_prompt
