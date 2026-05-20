import uuid
from fastapi import APIRouter, HTTPException

from app.database import get_db

router = APIRouter()


@router.post("/session", status_code=201)
def create_session():
    session_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sessions (id) VALUES (?)",
            (session_id,),
        )
    return {"session_id": session_id}
