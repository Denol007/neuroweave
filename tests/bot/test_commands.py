"""Tests for bot slash commands (consent + search)."""

from __future__ import annotations

from bot.cogs.consent import ConsentCog, ConsentView, _hash_user_id
from bot.cogs.search import SearchCog


class TestConsentCommand:
    def test_hash_user_id_deterministic(self):
        h1 = _hash_user_id(123)
        h2 = _hash_user_id(123)
        assert h1 == h2

    def test_hash_user_id_unique(self):
        assert _hash_user_id(123) != _hash_user_id(456)

    def test_hash_user_id_sha256(self):
        assert len(_hash_user_id(123)) == 64

    def test_consent_view_has_buttons(self):
        # ConsentView class should have the button methods
        assert hasattr(ConsentView, "kb_consent")
        assert hasattr(ConsentView, "ai_consent")
        assert hasattr(ConsentView, "both_consent")
        assert hasattr(ConsentView, "revoke")

    def test_consent_cog_has_privacy_command(self):
        assert hasattr(ConsentCog, "privacy")


class TestSearchCommand:
    def test_search_cog_has_nw_ask(self):
        assert hasattr(SearchCog, "nw_ask")

    def test_search_cog_setup_function(self):
        import inspect
        from bot.cogs import search
        assert inspect.iscoroutinefunction(search.setup)

    def test_consent_cog_setup_function(self):
        import inspect
        from bot.cogs import consent
        assert inspect.iscoroutinefunction(consent.setup)
