"""Tests for POST /api/session"""
import uuid


class TestCreateSession:
    def test_creates_session_returns_uuid(self, client):
        resp = client.post("/api/session")
        assert resp.status_code == 201
        body = resp.json()
        assert "session_id" in body
        # Must be a valid UUID
        uuid.UUID(body["session_id"])

    def test_each_call_returns_unique_id(self, client):
        ids = {client.post("/api/session").json()["session_id"] for _ in range(5)}
        assert len(ids) == 5, "Expected 5 unique session IDs"

    def test_session_stored_in_db(self, client):
        sid = client.post("/api/session").json()["session_id"]
        from tests.conftest import _shared_conn
        row = _shared_conn().execute(
            "SELECT id FROM sessions WHERE id = ?", (sid,)
        ).fetchone()
        assert row is not None, "Session not persisted to DB"
        assert row["id"] == sid

    def test_response_content_type_is_json(self, client):
        resp = client.post("/api/session")
        assert "application/json" in resp.headers["content-type"]

    def test_get_method_not_allowed(self, client):
        resp = client.get("/api/session")
        assert resp.status_code == 405
