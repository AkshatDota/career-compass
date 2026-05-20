import asyncio
import json
import logging

from fastapi import APIRouter, HTTPException, Query, Request

from app.ai_client import call_ai
from app.database import get_db
from app.limiter import limiter
from app.prompt_builder import build_prompt

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/results")
@limiter.limit("10/minute")
async def get_results(request: Request, session_id: str = Query(..., description="Session UUID")):
    with get_db() as conn:
        session = conn.execute(
            "SELECT id FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Return cached result if already generated
        cached = conn.execute(
            "SELECT result_json FROM results WHERE session_id = ?", (session_id,)
        ).fetchone()
        if cached:
            return json.loads(cached["result_json"])

        rows = conn.execute(
            """SELECT question_id, question_text, answer
               FROM answers WHERE session_id = ?
               ORDER BY answered_at""",
            (session_id,),
        ).fetchall()

    if len(rows) < 3:
        raise HTTPException(
            status_code=400,
            detail="Too few answers to generate a recommendation. Complete the quiz first.",
        )

    answers = [
        {"question_id": r["question_id"], "question_text": r["question_text"], "answer": r["answer"]}
        for r in rows
    ]
    system_prompt, user_prompt = build_prompt(answers)

    try:
        result = await asyncio.to_thread(call_ai, system_prompt, user_prompt)
    except json.JSONDecodeError:
        logger.exception("AI returned invalid JSON for session %s", session_id)
        raise HTTPException(status_code=502, detail="The AI returned an unexpected response. Please try again.")
    except Exception:
        logger.exception("AI provider error for session %s", session_id)
        raise HTTPException(status_code=502, detail="Could not reach the AI service. Please try again shortly.")

    result_json = json.dumps(result, ensure_ascii=False)
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO results (session_id, result_json) VALUES (?, ?)",
            (session_id, result_json),
        )
        conn.execute(
            "UPDATE sessions SET completed = 1 WHERE id = ?",
            (session_id,),
        )

    return result
