"""Tests for the Router Node."""

from unittest.mock import MagicMock, patch

from api.services.extraction.nodes.router import (
    route_after_classification,
    router_node,
)


class TestRouterNode:
    def _make_state(self, threads, idx=0):
        return {"threads": threads, "current_thread_idx": idx, "classification": "", "article_type": ""}

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_classifies_noise(self, mock_get_llm, noise_thread):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"classification": "NOISE", "reason": "greetings only"}')
        mock_get_llm.return_value = mock_llm
        result = router_node(self._make_state([noise_thread]))
        assert result["classification"] == "NOISE"
        assert result["article_type"] == ""

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_classifies_troubleshooting(self, mock_get_llm, tech_thread):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"classification": "TROUBLESHOOTING", "reason": "has error + code"}')
        mock_get_llm.return_value = mock_llm
        result = router_node(self._make_state([tech_thread]))
        assert result["classification"] == "TROUBLESHOOTING"
        assert result["article_type"] == "TROUBLESHOOTING"

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_classifies_question_answer(self, mock_get_llm, tech_thread):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"classification": "QUESTION_ANSWER", "reason": "how-to question"}')
        mock_get_llm.return_value = mock_llm
        result = router_node(self._make_state([tech_thread]))
        assert result["classification"] == "QUESTION_ANSWER"

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_defaults_to_question_answer_on_ambiguity(self, mock_get_llm, tech_thread):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="I'm not sure about this one")
        mock_get_llm.return_value = mock_llm
        result = router_node(self._make_state([tech_thread]))
        assert result["classification"] == "QUESTION_ANSWER"


class TestRouteAfterClassification:
    def test_noise_ends(self):
        assert route_after_classification({"classification": "NOISE"}) == "__end__"

    def test_non_noise_to_evaluator(self):
        for cat in ("TROUBLESHOOTING", "QUESTION_ANSWER", "GUIDE", "DISCUSSION_SUMMARY"):
            assert route_after_classification({"classification": cat}) == "evaluator"
