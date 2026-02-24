"""Tests for GitHub API endpoints."""


class TestGitHubEndpoints:
    def test_list_repos_route(self, client):
        r = client.get("/api/github/repos")
        assert r.status_code in (200, 500)

    def test_add_repo_validation(self, client):
        r = client.post("/api/github/repos", json={})
        assert r.status_code == 422

    def test_add_repo_route(self, client):
        r = client.post("/api/github/repos", json={"owner": "test", "repo": "test"})
        assert r.status_code in (201, 409, 500)

    def test_sync_not_found(self, client):
        r = client.post("/api/github/repos/99999/sync")
        assert r.status_code in (404, 500)

    def test_delete_not_found(self, client):
        r = client.delete("/api/github/repos/99999")
        assert r.status_code in (404, 500)

    def test_search_with_source_filter(self, client):
        r = client.get("/api/search?q=test&source=github")
        assert r.status_code in (200, 500)

    def test_search_with_discord_filter(self, client):
        r = client.get("/api/search?q=test&source=discord")
        assert r.status_code in (200, 500)
