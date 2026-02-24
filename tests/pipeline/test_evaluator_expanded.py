"""Tests for expanded Evaluator — type-aware routing."""

from api.services.extraction.nodes.evaluator import route_after_evaluation


class TestEvaluatorTypeAwareRouting:
    def test_troubleshooting_needs_code_or_resolution(self):
        # has_solution + has_code → compiler
        state = {"evaluation": {"has_solution": True, "has_code": True, "is_resolved": False, "reasoning": ""}, "article_type": "TROUBLESHOOTING"}
        assert route_after_evaluation(state) == "compiler"

        # has_solution + is_resolved → compiler
        state = {"evaluation": {"has_solution": True, "has_code": False, "is_resolved": True, "reasoning": ""}, "article_type": "TROUBLESHOOTING"}
        assert route_after_evaluation(state) == "compiler"

        # has_solution only (no code, no resolution) → checkpoint
        state = {"evaluation": {"has_solution": True, "has_code": False, "is_resolved": False, "reasoning": ""}, "article_type": "TROUBLESHOOTING"}
        assert route_after_evaluation(state) == "__end__"

    def test_question_answer_no_code_required(self):
        # has_solution, no code → compiler
        state = {"evaluation": {"has_solution": True, "has_code": False, "is_resolved": False, "reasoning": ""}, "article_type": "QUESTION_ANSWER"}
        assert route_after_evaluation(state) == "compiler"

        # no solution → end
        state = {"evaluation": {"has_solution": False, "has_code": False, "is_resolved": False, "reasoning": ""}, "article_type": "QUESTION_ANSWER"}
        assert route_after_evaluation(state) == "__end__"

    def test_guide_always_passes(self):
        # Even with no solution/code/resolution → compiler
        state = {"evaluation": {"has_solution": False, "has_code": False, "is_resolved": False, "reasoning": ""}, "article_type": "GUIDE"}
        assert route_after_evaluation(state) == "compiler"

    def test_discussion_summary_always_passes(self):
        state = {"evaluation": {"has_solution": False, "has_code": False, "is_resolved": False, "reasoning": ""}, "article_type": "DISCUSSION_SUMMARY"}
        assert route_after_evaluation(state) == "compiler"

    def test_no_evaluation_ends(self):
        assert route_after_evaluation({"evaluation": None, "article_type": "QUESTION_ANSWER"}) == "__end__"

    def test_missing_article_type_defaults_to_troubleshooting(self):
        # Without article_type, falls back to TROUBLESHOOTING logic
        state = {"evaluation": {"has_solution": True, "has_code": False, "is_resolved": False, "reasoning": ""}}
        assert route_after_evaluation(state) == "__end__"  # No code = checkpoint for troubleshooting
