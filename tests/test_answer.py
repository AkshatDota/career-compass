"""Tests for POST /api/answer"""
import json
from tests.conftest import _shared_conn


class TestSubmitAnswer:
    def test_returns_ok_true(self, client, session_id):
        resp = client.post("/api/answer", json={
            "session_id": session_id,
            "question_id": "energy",
            "question_text": "What energizes you?",
            "answer": "Solving complex problems",
        })
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

    def test_stores_string_answer_in_db(self, client, session_id):
        client.post("/api/answer", json={
            "session_id": session_id,
            "question_id": "energy",
            "question_text": "What energizes you?",
            "answer": "Solving complex problems",
        })
        row = _shared_conn().execute(
            "SELECT answer, question_text FROM answers WHERE session_id=? AND question_id=?",
            (session_id, "energy"),
        ).fetchone()
        assert row is not None
        assert row["answer"] == "Solving complex problems"
        assert row["question_text"] == "What energizes you?"

    def test_stores_list_answer_as_json(self, client, session_id):
        client.post("/api/answer", json={
            "session_id": session_id,
            "question_id": "subjects",
            "answer": ["Computers & coding", "Math & statistics"],
        })
        row = _shared_conn().execute(
            "SELECT answer FROM answers WHERE session_id=? AND question_id=?",
            (session_id, "subjects"),
        ).fetchone()
        parsed = json.loads(row["answer"])
        assert parsed == ["Computers & coding", "Math & statistics"]

    def test_upsert_overwrites_previous_answer(self, client, session_id):
        """Re-answering the same question (back-navigation) should overwrite."""
        for answer in ("First answer", "Updated answer"):
            client.post("/api/answer", json={
                "session_id": session_id,
                "question_id": "energy",
                "answer": answer,
            })
        rows = _shared_conn().execute(
            "SELECT answer FROM answers WHERE session_id=? AND question_id=?",
            (session_id, "energy"),
        ).fetchall()
        assert len(rows) == 1, "Should have exactly 1 row after upsert"
        assert rows[0]["answer"] == "Updated answer"

    def test_invalid_session_returns_404(self, client):
        resp = client.post("/api/answer", json={
            "session_id": "nonexistent",
            "question_id": "energy",
            "answer": "Something",
        })
        assert resp.status_code == 404

    def test_missing_body_returns_422(self, client):
        resp = client.post("/api/answer", json={})
        assert resp.status_code == 422

    def test_question_text_is_optional(self, client, session_id):
        """question_text is optional — backend should accept answers without it."""
        resp = client.post("/api/answer", json={
            "session_id": session_id,
            "question_id": "energy",
            "answer": "Solving problems",
        })
        assert resp.status_code == 200

    def test_multiple_different_questions_stored(self, client, session_id):
        for qid, ans in [("energy", "Solving problems"), ("risk", "I love risk")]:
            client.post("/api/answer", json={
                "session_id": session_id,
                "question_id": qid,
                "answer": ans,
            })
        count = _shared_conn().execute(
            "SELECT COUNT(*) FROM answers WHERE session_id=?", (session_id,)
        ).fetchone()[0]
        assert count == 2

    def test_answers_isolated_between_sessions(self, client):
        s1 = client.post("/api/session").json()["session_id"]
        s2 = client.post("/api/session").json()["session_id"]

        client.post("/api/answer", json={"session_id": s1, "question_id": "energy", "answer": "A"})
        client.post("/api/answer", json={"session_id": s2, "question_id": "energy", "answer": "B"})

        r1 = _shared_conn().execute(
            "SELECT answer FROM answers WHERE session_id=?", (s1,)
        ).fetchone()
        r2 = _shared_conn().execute(
            "SELECT answer FROM answers WHERE session_id=?", (s2,)
        ).fetchone()
        assert r1["answer"] == "A"
        assert r2["answer"] == "B"
