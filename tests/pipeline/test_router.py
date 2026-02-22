"""Tests for the Router Node."""

from unittest.mock import MagicMock, patch

from api.services.extraction.nodes.router import (
    route_after_classification,
    router_node,
)


class TestRouterNode:
    def _make_state(self, threads, idx=0):
        return {
            "threads": threads,
            "current_thread_idx": idx,
            "classification": "",
        }

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_classifies_noise(self, mock_get_llm, noise_thread):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"classification": "NOISE", "reason": "greetings only"}')
        mock_get_llm.return_value = mock_llm

        state = self._make_state([noise_thread])
        result = router_node(state)
        assert result["classification"] == "NOISE"

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_classifies_technical(self, mock_get_llm, tech_thread):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"classification": "TECHNICAL", "reason": "has error + code"}')
        mock_get_llm.return_value = mock_llm

        state = self._make_state([tech_thread])
        result = router_node(state)
        assert result["classification"] == "TECHNICAL"

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_defaults_to_technical_on_ambiguity(self, mock_get_llm, tech_thread):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="I'm not sure about this one")
        mock_get_llm.return_value = mock_llm

        state = self._make_state([tech_thread])
        result = router_node(state)
        assert result["classification"] == "TECHNICAL"


class TestRouteAfterClassification:
    def test_noise_ends(self):
        assert route_after_classification({"classification": "NOISE"}) == "__end__"

    def test_technical_to_evaluator(self):
        assert route_after_classification({"classification": "TECHNICAL"}) == "evaluator"
