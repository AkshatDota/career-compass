import json
from typing import Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.database import get_db

router = APIRouter()


class AnswerPayload(BaseModel):
    session_id: str
    question_id: str = Field(max_length=100)
    question_text: Optional[str] = Field(None, max_length=500)
    answer: Union[str, list[str]]

    @field_validator("answer")
    @classmethod
    def validate_answer_length(cls, v: Union[str, list[str]]) -> Union[str, list[str]]:
        if isinstance(v, str):
            if len(v) > 2000:
                raise ValueError("Answer exceeds maximum length of 2000 characters")
        else:
            for item in v:
                if len(str(item)) > 2000:
                    raise ValueError("Answer option exceeds maximum length of 2000 characters")
        return v


@router.post("/answer")
def submit_answer(payload: AnswerPayload):
    # Normalise multi-select to JSON string
    if isinstance(payload.answer, list):
        stored_answer = json.dumps(payload.answer, ensure_ascii=False)
    else:
        stored_answer = payload.answer

    with get_db() as conn:
        session = conn.execute(
            "SELECT id FROM sessions WHERE id = ?", (payload.session_id,)
        ).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        # Upsert: delete previous answer for this question, then insert fresh.
        # Also clear any cached result — re-answering invalidates the old recommendation.
        conn.execute(
            "DELETE FROM answers WHERE session_id = ? AND question_id = ?",
            (payload.session_id, payload.question_id),
        )
        conn.execute(
            "DELETE FROM results WHERE session_id = ?",
            (payload.session_id,),
        )
        conn.execute(
            """INSERT INTO answers (session_id, question_id, question_text, answer)
               VALUES (?, ?, ?, ?)""",
            (payload.session_id, payload.question_id, payload.question_text, stored_answer),
        )

    return {"ok": True}
