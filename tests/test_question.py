"""Tests for GET /api/question"""
import json


class TestGetQuestion:
    def test_first_question_is_q1(self, client, session_id):
        resp = client.get(f"/api/question?session_id={session_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["question_id"] == "q1"
        assert "text" in body
        assert "type" in body
        assert "options" in body
        assert isinstance(body["options"], list)

    def test_progress_starts_at_one(self, client, session_id):
        resp = client.get(f"/api/question?session_id={session_id}")
        prog = resp.json()["progress"]
        assert prog["current"] == 1
        assert prog["total"] >= 8

    def test_returns_done_when_all_answered(self, client, session_id):
        # Answer all 8 base questions
        base_ids = ["q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8"]
        for qid in base_ids:
            client.post("/api/answer", json={
                "session_id": session_id,
                "question_id": qid,
                "question_text": f"Question {qid}",
                "answer": "Some answer",
            })
        resp = client.get(f"/api/question?session_id={session_id}")
        assert resp.json().get("done") is True

    def test_adaptive_followup_injected_after_q1_technology(self, client, session_id):
        # Answer q1 with Technology — should inject q_tech
        client.post("/api/answer", json={
            "session_id": session_id,
            "question_id": "q1",
            "question_text": "Which broad areas excite you?",
            "answer": json.dumps(["Technology"]),
        })
        resp = client.get(f"/api/question?session_id={session_id}")
        assert resp.json()["question_id"] == "q_tech"

    def test_adaptive_followup_for_multiple_areas(self, client, session_id):
        # Technology + Business → q_tech next, q_biz after that, then q2
        client.post("/api/answer", json={
            "session_id": session_id,
            "question_id": "q1",
            "answer": json.dumps(["Technology", "Business"]),
        })
        q2 = client.get(f"/api/question?session_id={session_id}").json()
        assert q2["question_id"] == "q_tech"
        client.post("/api/answer", json={
            "session_id": session_id, "question_id": "q_tech", "answer": "Software dev"
        })
        q3 = client.get(f"/api/question?session_id={session_id}").json()
        assert q3["question_id"] == "q_biz"

    def test_missing_session_id_param(self, client):
        resp = client.get("/api/question")
        assert resp.status_code == 422

    def test_invalid_session_id_returns_404(self, client):
        resp = client.get("/api/question?session_id=nonexistent")
        assert resp.status_code == 404

    def test_progress_increments_after_each_answer(self, client, session_id):
        q1 = client.get(f"/api/question?session_id={session_id}").json()
        assert q1["progress"]["current"] == 1

        client.post("/api/answer", json={
            "session_id": session_id, "question_id": "q1", "answer": "Some answer"
        })
        q2 = client.get(f"/api/question?session_id={session_id}").json()
        assert q2["progress"]["current"] == 2
