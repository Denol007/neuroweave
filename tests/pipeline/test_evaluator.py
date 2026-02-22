"""Tests for the Evaluator Node."""

from unittest.mock import MagicMock, patch

from api.services.extraction.nodes.evaluator import (
    _parse_evaluation,
    evaluator_node,
    route_after_evaluation,
)


class TestParseEvaluation:
    def test_valid_json(self):
        result = _parse_evaluation('{"has_solution": true, "has_code": true, "is_resolved": true, "reasoning": "OP confirmed"}')
        assert result["is_resolved"] is True
        assert result["has_solution"] is True
        assert result["has_code"] is True
        assert "OP confirmed" in result["reasoning"]

    def test_markdown_wrapped_json(self):
        result = _parse_evaluation('```json\n{"has_solution": false, "has_code": false, "is_resolved": false, "reasoning": "no fix"}\n```')
        assert result["is_resolved"] is False

    def test_malformed_json_graceful(self):
        result = _parse_evaluation("This is not JSON at all")
        assert result["is_resolved"] is False
        assert result["has_solution"] is False
        assert "Failed to parse" in result["reasoning"]

    def test_partial_json(self):
        result = _parse_evaluation('{"has_solution": true}')
        assert result["has_solution"] is True
        assert result["is_resolved"] is False  # Missing defaults to False
        assert result["has_code"] is False


class TestEvaluatorNode:
    @patch("api.services.extraction.nodes.evaluator._get_llm")
    def test_resolved_thread(self, mock_get_llm, tech_thread):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='{"has_solution": true, "has_code": true, "is_resolved": true, "reasoning": "User confirmed fix"}'
        )
        mock_get_llm.return_value = mock_llm

        state = {"threads": [tech_thread], "current_thread_idx": 0}
        result = evaluator_node(state)

        assert result["evaluation"]["is_resolved"] is True
        assert result["evaluation"]["has_code"] is True

    @patch("api.services.extraction.nodes.evaluator._get_llm")
    def test_unresolved_thread(self, mock_get_llm, tech_thread):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(
            content='{"has_solution": false, "has_code": false, "is_resolved": false, "reasoning": "No solution proposed"}'
        )
        mock_get_llm.return_value = mock_llm

        state = {"threads": [tech_thread], "current_thread_idx": 0}
        result = evaluator_node(state)

        assert result["evaluation"]["is_resolved"] is False


class TestRouteAfterEvaluation:
    def test_resolved_with_code_goes_to_compiler(self):
        state = {"evaluation": {"has_solution": True, "has_code": True, "is_resolved": True, "reasoning": ""}}
        assert route_after_evaluation(state) == "compiler"

    def test_has_solution_and_code_goes_to_compiler(self):
        state = {"evaluation": {"has_solution": True, "has_code": True, "is_resolved": False, "reasoning": ""}}
        assert route_after_evaluation(state) == "compiler"

    def test_no_solution_checkpoints(self):
        state = {"evaluation": {"has_solution": False, "has_code": False, "is_resolved": False, "reasoning": ""}}
        assert route_after_evaluation(state) == "__end__"

    def test_no_evaluation_ends(self):
        assert route_after_evaluation({"evaluation": None}) == "__end__"
        assert route_after_evaluation({}) == "__end__"
