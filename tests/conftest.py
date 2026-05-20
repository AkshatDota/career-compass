"""
Shared pytest fixtures for Career Discovery backend tests.
Uses an in-memory SQLite database so tests are fully isolated.
"""
import os
import pytest
from fastapi.testclient import TestClient

# Point all modules at an in-memory DB before importing anything from app
os.environ.setdefault("AI_PROVIDER", "groq")
os.environ.setdefault("GROQ_API_KEY",    "test-groq-key")
os.environ.setdefault("GEMINI_API_KEY",  "test-gemini-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ["DB_PATH"] = ":memory:"

from app.database import init_db, get_db
import main as app_module

# ------------------------------------------------------------------
# Patch get_db to return a *single* shared in-memory connection
# so all open() calls in a test see the same data.
# ------------------------------------------------------------------
import sqlite3
from contextlib import contextmanager

_CONN: sqlite3.Connection | None = None


def _shared_conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        _CONN = sqlite3.connect(":memory:", check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
    return _CONN


@contextmanager
def _test_get_db():
    conn = _shared_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Clear the in-memory rate-limit counters before every test."""
    from app.limiter import limiter
    limiter._storage.reset()
    yield
    limiter._storage.reset()


@pytest.fixture(autouse=True)
def reset_db(monkeypatch):
    """Re-create schema on a fresh in-memory connection before every test."""
    global _CONN
    _CONN = sqlite3.connect(":memory:", check_same_thread=False)
    _CONN.row_factory = sqlite3.Row
    _CONN.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed BOOLEAN DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            question_text TEXT,
            answer TEXT NOT NULL,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS results (
            session_id TEXT PRIMARY KEY,
            result_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
    """)
    _CONN.commit()

    # Patch get_db everywhere it's imported
    import app.database as db_module
    import app.routers.session as sess_mod
    import app.routers.question as quest_mod
    import app.routers.answer as ans_mod
    import app.routers.results as res_mod

    for mod in (db_module, sess_mod, quest_mod, ans_mod, res_mod):
        monkeypatch.setattr(mod, "get_db", _test_get_db)


@pytest.fixture
def client():
    with TestClient(app_module.app) as c:
        yield c


@pytest.fixture
def session_id(client):
    """Create a fresh session and return its ID."""
    resp = client.post("/api/session")
    assert resp.status_code == 201
    return resp.json()["session_id"]


SAMPLE_ANSWERS = [
    {"question_id": "energy",      "question_text": "What energizes you?",            "answer": "Solving complex problems"},
    {"question_id": "environment", "question_text": "Preferred environment?",          "answer": "Fast-paced startup"},
    {"question_id": "subjects",    "question_text": "Subjects you enjoyed?",           "answer": '["Computers & coding", "Math & statistics"]'},
    {"question_id": "communicate", "question_text": "How do you communicate?",         "answer": "With numbers and evidence"},
    {"question_id": "values",      "question_text": "What matters most in a job?",     "answer": '["High earning potential", "Fast skill growth"]'},
    {"question_id": "develop",     "question_text": "Skills you want to develop?",     "answer": '["Coding & engineering", "Data analysis"]'},
    {"question_id": "problem",     "question_text": "How do you tackle problems?",     "answer": "Break it into steps"},
    {"question_id": "workday",     "question_text": "Ideal workday?",                  "answer": "A bit of everything"},
    {"question_id": "risk",        "question_text": "How do you handle risk?",         "answer": "Comfortable in doses"},
    {"question_id": "drawn",       "question_text": "What do you work best with?",     "answer": "Data and numbers"},
    {"question_id": "fiveyears",   "question_text": "Where in five years?",            "answer": "Recognised expert"},
    {"question_id": "study",       "question_text": "How much study time is fine?",    "answer": "A few years is fine"},
]


MOCK_RESULT = {
    "careers": [
        {
            "title": "Data Scientist",
            "tagline": "Turn data into decisions.",
            "why_it_fits": "Strong analytical skills and coding ability.",
            "salary": {"fresher": "₹6–12 LPA", "mid_level": "₹18–35 LPA", "senior": "₹50–100 LPA"},
            "skills_to_build": ["Python", "SQL", "ML", "Viz"],
            "roadmap": ["Step 1: Learn Python", "Step 2: Build projects", "Step 3: Get certified"],
            "top_companies": ["Google", "Microsoft", "Flipkart"],
        }
    ],
    "summary": "You have great potential. Focus on data and you'll go far.",
}
