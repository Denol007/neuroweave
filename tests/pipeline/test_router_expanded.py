"""Tests for expanded Router — 5 categories."""

from unittest.mock import MagicMock, patch

from api.services.extraction.nodes.router import route_after_classification, router_node
from api.services.extraction.state import ARTICLE_TYPES


class TestRouterCategories:
    def _state(self, thread):
        return {"threads": [thread], "current_thread_idx": 0, "classification": "", "article_type": ""}

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_troubleshooting(self, mock, tech_thread):
        mock.return_value.invoke.return_value = MagicMock(content='{"classification":"TROUBLESHOOTING"}')
        r = router_node(self._state(tech_thread))
        assert r["classification"] == "TROUBLESHOOTING"
        assert r["article_type"] == "TROUBLESHOOTING"

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_question_answer(self, mock, tech_thread):
        mock.return_value.invoke.return_value = MagicMock(content='{"classification":"QUESTION_ANSWER"}')
        r = router_node(self._state(tech_thread))
        assert r["classification"] == "QUESTION_ANSWER"
        assert r["article_type"] == "QUESTION_ANSWER"

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_guide(self, mock, tech_thread):
        mock.return_value.invoke.return_value = MagicMock(content='{"classification":"GUIDE"}')
        r = router_node(self._state(tech_thread))
        assert r["classification"] == "GUIDE"

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_discussion_summary(self, mock, tech_thread):
        mock.return_value.invoke.return_value = MagicMock(content='{"classification":"DISCUSSION_SUMMARY"}')
        r = router_node(self._state(tech_thread))
        assert r["classification"] == "DISCUSSION_SUMMARY"

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_noise(self, mock, noise_thread):
        mock.return_value.invoke.return_value = MagicMock(content='{"classification":"NOISE"}')
        r = router_node(self._state(noise_thread))
        assert r["classification"] == "NOISE"
        assert r["article_type"] == ""

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_ambiguous_defaults_to_question_answer(self, mock, tech_thread):
        mock.return_value.invoke.return_value = MagicMock(content="unclear response here")
        r = router_node(self._state(tech_thread))
        assert r["classification"] == "QUESTION_ANSWER"


class TestRouteAfterClassificationExpanded:
    def test_noise_ends(self):
        assert route_after_classification({"classification": "NOISE"}) == "__end__"

    def test_all_article_types_go_to_evaluator(self):
        for cat in ARTICLE_TYPES:
            assert route_after_classification({"classification": cat}) == "evaluator", f"{cat} should → evaluator"
