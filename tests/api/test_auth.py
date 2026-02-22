"""Tests for Auth API endpoints."""


class TestAuth:
    def test_discord_redirect_no_config(self, client):
        """Without DISCORD_CLIENT_ID, should return 503."""
        r = client.get("/api/auth/discord")
        assert r.status_code == 503

    def test_callback_no_config(self, client):
        """Without Discord config, callback should return 503."""
        r = client.get("/api/auth/discord/callback?code=test123")
        assert r.status_code == 503

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
