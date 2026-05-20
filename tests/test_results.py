"""Tests for GET /api/results"""
import json
import pytest
from unittest.mock import patch
from tests.conftest import SAMPLE_ANSWERS, MOCK_RESULT


def _fill_answers(client, session_id, answers=None):
    for a in (answers or SAMPLE_ANSWERS):
        client.post("/api/answer", json={"session_id": session_id, **a})


class TestGetResults:
    def test_returns_404_for_unknown_session(self, client):
        resp = client.get("/api/results?session_id=nonexistent")
        assert resp.status_code == 404

    def test_returns_400_with_too_few_answers(self, client, session_id):
        # Only 2 answers — below the minimum of 3
        for a in SAMPLE_ANSWERS[:2]:
            client.post("/api/answer", json={"session_id": session_id, **a})
        resp = client.get(f"/api/results?session_id={session_id}")
        assert resp.status_code == 400
        assert "Too few answers" in resp.json()["detail"]

    def test_returns_ai_result_with_correct_structure(self, client, session_id):
        _fill_answers(client, session_id)
        with patch("app.routers.results.call_ai", return_value=MOCK_RESULT):
            resp = client.get(f"/api/results?session_id={session_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert "careers" in body
        assert "summary" in body
        assert isinstance(body["careers"], list)
        assert len(body["careers"]) >= 1

    def test_career_has_all_required_fields(self, client, session_id):
        _fill_answers(client, session_id)
        with patch("app.routers.results.call_ai", return_value=MOCK_RESULT):
            body = client.get(f"/api/results?session_id={session_id}").json()
        career = body["careers"][0]
        for field in ("title", "tagline", "why_it_fits", "salary", "skills_to_build", "roadmap", "top_companies"):
            assert field in career, f"Missing field: {field}"

    def test_salary_has_three_tiers(self, client, session_id):
        _fill_answers(client, session_id)
        with patch("app.routers.results.call_ai", return_value=MOCK_RESULT):
            body = client.get(f"/api/results?session_id={session_id}").json()
        salary = body["careers"][0]["salary"]
        assert "fresher" in salary
        assert "mid_level" in salary
        assert "senior" in salary

    def test_result_is_cached_on_second_call(self, client, session_id):
        _fill_answers(client, session_id)
        call_count = {"n": 0}

        def fake_ai(*args, **kwargs):
            call_count["n"] += 1
            return MOCK_RESULT

        with patch("app.routers.results.call_ai", side_effect=fake_ai):
            client.get(f"/api/results?session_id={session_id}")
            client.get(f"/api/results?session_id={session_id}")

        assert call_count["n"] == 1, "AI should only be called once; second call should use cache"

    def test_cached_result_matches_original(self, client, session_id):
        _fill_answers(client, session_id)
        with patch("app.routers.results.call_ai", return_value=MOCK_RESULT):
            r1 = client.get(f"/api/results?session_id={session_id}").json()
            r2 = client.get(f"/api/results?session_id={session_id}").json()
        assert r1 == r2

    def test_result_stored_in_db(self, client, session_id):
        from tests.conftest import _shared_conn
        _fill_answers(client, session_id)
        with patch("app.routers.results.call_ai", return_value=MOCK_RESULT):
            client.get(f"/api/results?session_id={session_id}")
        row = _shared_conn().execute(
            "SELECT result_json FROM results WHERE session_id=?", (session_id,)
        ).fetchone()
        assert row is not None
        stored = json.loads(row["result_json"])
        assert stored["careers"][0]["title"] == "Data Scientist"

    def test_missing_session_id_param(self, client):
        resp = client.get("/api/results")
        assert resp.status_code == 422

    def test_ai_error_returns_502(self, client, session_id):
        _fill_answers(client, session_id)
        with patch("app.routers.results.call_ai", side_effect=Exception("API timeout")):
            resp = client.get(f"/api/results?session_id={session_id}")
        assert resp.status_code == 502
        assert "AI service" in resp.json()["detail"]

    def test_ai_invalid_json_returns_502(self, client, session_id):
        _fill_answers(client, session_id)
        with patch("app.routers.results.call_ai", side_effect=json.JSONDecodeError("bad", "", 0)):
            resp = client.get(f"/api/results?session_id={session_id}")
        assert resp.status_code == 502


class TestHealth:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
