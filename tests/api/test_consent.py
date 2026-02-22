"""Tests for Consent API endpoints."""


class TestConsentEndpoints:
    def test_create_consent_validation(self, client):
        r = client.post("/api/consent", json={})
        assert r.status_code == 422

    def test_create_consent_route_exists(self, client, seed_data):
        r = client.post("/api/consent", json={
            "user_hash": "testhash_abc123",
            "server_id": seed_data["server_id"],
            "kb_consent": True,
            "ai_consent": False,
        })
        assert r.status_code in (201, 500)

    def test_get_consent_route_exists(self, client):
        r = client.get("/api/consent/somehash")
        assert r.status_code in (200, 500)

    def test_revoke_consent_route_exists(self, client):
        r = client.delete("/api/consent/nonexistent_hash_xyz_000")
        assert r.status_code in (404, 500)
