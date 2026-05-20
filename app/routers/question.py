from fastapi import APIRouter, HTTPException, Query

from app.database import get_db
from app.questions import get_next_question

router = APIRouter()


def _build_question_response(session_id: str) -> dict:
    with get_db() as conn:
        session = conn.execute(
            "SELECT id FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        rows = conn.execute(
            "SELECT question_id, answer FROM answers WHERE session_id = ? ORDER BY answered_at",
            (session_id,),
        ).fetchall()

    answered = [{"question_id": r["question_id"], "answer": r["answer"]} for r in rows]
    question, current, total = get_next_question(answered)

    if question is None:
        return {"done": True}

    return {
        "question_id": question["id"],
        "text": question["text"],
        "type": question["type"],
        "options": question["options"],
        "progress": {"current": current, "total": total},
    }


@router.get("/question")
def get_question(session_id: str = Query(..., description="Session UUID")):
    return _build_question_response(session_id)
