"""Tests for the Quality Gate."""

from api.services.extraction.nodes.quality_gate import (
    MAX_RETRIES,
    QUALITY_THRESHOLD,
    compute_quality_score,
    quality_gate_node,
    route_after_quality,
)


class TestComputeQualityScore:
    def test_high_quality_passes(self, high_quality_article):
        score = compute_quality_score(high_quality_article)
        assert score >= QUALITY_THRESHOLD
        assert score <= 1.0

    def test_low_quality_fails(self, low_quality_article):
        score = compute_quality_score(low_quality_article)
        assert score < QUALITY_THRESHOLD

    def test_none_article_scores_zero(self):
        assert compute_quality_score(None) == 0.0

    def test_empty_dict_scores_zero(self):
        assert compute_quality_score({}) == 0.0

    def test_score_components(self):
        """Verify each scoring factor contributes correctly."""
        # Only solution
        only_solution = {"solution": "x" * 201, "diagnosis": "", "tags": [], "confidence": 0, "thread_summary": ""}
        assert compute_quality_score(only_solution) == 0.25

        # Only code
        only_code = {"solution": "", "code_snippet": "x" * 51, "diagnosis": "", "tags": [], "confidence": 0, "thread_summary": ""}
        assert compute_quality_score(only_code) == 0.20

        # Max confidence contribution
        only_conf = {"solution": "", "diagnosis": "", "tags": [], "confidence": 1.0, "thread_summary": ""}
        assert compute_quality_score(only_conf) == 0.20

    def test_score_never_exceeds_one(self, high_quality_article):
        # Boost all factors to max
        article = {**high_quality_article, "confidence": 1.0}
        score = compute_quality_score(article)
        assert score <= 1.0


class TestQualityGateNode:
    def test_pass_updates_score(self, high_quality_article):
        state = {"compiled_article": high_quality_article, "quality_score": 0, "retry_count": 0}
        result = quality_gate_node(state)
        assert result["quality_score"] >= QUALITY_THRESHOLD
        assert result["retry_count"] == 0  # No increment on pass

    def test_fail_increments_retry(self, low_quality_article):
        state = {"compiled_article": low_quality_article, "quality_score": 0, "retry_count": 0}
        result = quality_gate_node(state)
        assert result["quality_score"] < QUALITY_THRESHOLD
        assert result["retry_count"] == 1


class TestRouteAfterQuality:
    def test_pass_ends(self):
        state = {"quality_score": 0.85, "retry_count": 0}
        assert route_after_quality(state) == "__end__"

    def test_fail_retries_compiler(self):
        state = {"quality_score": 0.3, "retry_count": 1}
        assert route_after_quality(state) == "compiler"

    def test_max_retries_rejects(self):
        state = {"quality_score": 0.3, "retry_count": MAX_RETRIES}
        assert route_after_quality(state) == "__end__"

    def test_exact_threshold_passes(self):
        state = {"quality_score": QUALITY_THRESHOLD, "retry_count": 0}
        assert route_after_quality(state) == "__end__"
