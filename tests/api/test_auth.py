"""Tests for Auth API endpoints."""


class TestAuth:
    def test_discord_redirect(self, client):
        """Discord redirect should return redirect URL or 503 if not configured."""
        r = client.get("/api/auth/discord")
        assert r.status_code in (200, 503)

    def test_callback_invalid_code(self, client):
        """Invalid code should fail with 401 or 503."""
        r = client.get("/api/auth/discord/callback?code=invalid_test_code")
        assert r.status_code in (401, 503, 302)  # 302 if redirect on error

    def test_me_no_auth(self, client):
        """Without token, /me should return 401."""
        r = client.get("/api/auth/me")
        assert r.status_code == 401

    def test_me_with_auth(self, client, auth_headers):
        """With valid JWT, /me returns user info."""
        r = client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["discord_id"] == "123456"
        assert data["username"] == "testuser"

    def test_me_invalid_token(self, client):
        """Invalid JWT should return 401."""
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert r.status_code == 401


class TestHealthCheck:
    def test_health(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
