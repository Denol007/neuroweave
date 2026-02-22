"""Tests for the Consent Checker service."""

from unittest.mock import MagicMock, patch

from api.services.consent_checker import filter_consented_messages, get_consented_users


class TestGetConsentedUsers:
    @patch("api.services.consent_checker.Session")
    def test_returns_consented_hashes(self, mock_session_cls):
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchall.return_value = [
            ("hash_aaa",), ("hash_bbb",),
        ]
        mock_session_cls.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_session_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = get_consented_users("server_123")
        assert result == {"hash_aaa", "hash_bbb"}

    @patch("api.services.consent_checker.Session")
    def test_db_error_returns_empty(self, mock_session_cls):
        mock_session_cls.return_value.__enter__ = MagicMock(side_effect=Exception("DB down"))

        result = get_consented_users("server_123")
        assert result == set()


class TestFilterConsentedMessages:
    @patch("api.services.consent_checker.get_consented_users")
    def test_filters_non_consented(self, mock_get):
        mock_get.return_value = {"hash_aaa", "hash_bbb"}

        messages = [
            {"author_hash": "hash_aaa", "content": "ok"},
            {"author_hash": "hash_ccc", "content": "no consent"},
            {"author_hash": "hash_bbb", "content": "ok too"},
        ]

        filtered, excluded = filter_consented_messages(messages, "srv1")
        assert len(filtered) == 2
        assert excluded == 1
        assert all(m["author_hash"] in {"hash_aaa", "hash_bbb"} for m in filtered)

    @patch("api.services.consent_checker.get_consented_users")
    def test_no_consented_users_returns_empty(self, mock_get):
        mock_get.return_value = set()

        messages = [
            {"author_hash": "hash_aaa", "content": "msg"},
        ]

        filtered, excluded = filter_consented_messages(messages, "srv1")
        assert len(filtered) == 0
        assert excluded == 1

    @patch("api.services.consent_checker.get_consented_users")
    def test_all_consented(self, mock_get):
        mock_get.return_value = {"hash_aaa", "hash_bbb"}

        messages = [
            {"author_hash": "hash_aaa", "content": "msg1"},
            {"author_hash": "hash_bbb", "content": "msg2"},
        ]

        filtered, excluded = filter_consented_messages(messages, "srv1")
        assert len(filtered) == 2
        assert excluded == 0

    @patch("api.services.consent_checker.get_consented_users")
    def test_empty_messages(self, mock_get):
        mock_get.return_value = {"hash_aaa"}

        filtered, excluded = filter_consented_messages([], "srv1")
        assert len(filtered) == 0
        assert excluded == 0
