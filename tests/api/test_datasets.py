"""Tests for Datasets API endpoints."""


class TestDatasetEndpoints:
    def test_export_requires_auth(self, client):
        r = client.post("/api/datasets/export", json={"server_id": 1})
        assert r.status_code == 401

    def test_list_exports_route_exists(self, client):
        r = client.get("/api/datasets")
        assert r.status_code in (200, 500)

    def test_download_not_found(self, client):
        r = client.get("/api/datasets/99999/download")
        assert r.status_code in (404, 500)
