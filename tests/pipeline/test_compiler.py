"""Tests for the Compiler Node."""

from unittest.mock import MagicMock, patch

from api.services.extraction.nodes.compiler import (
    ExtractedKnowledge,
    compiler_node,
)


class TestExtractedKnowledgeSchema:
    def test_valid_article(self, high_quality_article):
        ek = ExtractedKnowledge(**high_quality_article)
        assert ek.confidence == 0.92
        assert len(ek.tags) == 6
        assert ek.language == "javascript"
        assert ek.code_snippet is not None

    def test_null_code_snippet(self):
        ek = ExtractedKnowledge(
            article_type="troubleshooting",
            symptom="error", diagnosis="cause", solution="fix",
            code_snippet=None, language="python", framework=None,
            tags=["bug"], confidence=0.5, thread_summary="summary",
        )
        assert ek.code_snippet is None

    def test_confidence_bounds(self):
        import pytest
        with pytest.raises(Exception):
            ExtractedKnowledge(
                article_type="troubleshooting",
                symptom="x", diagnosis="x", solution="x",
                language="python", tags=["x"], confidence=1.5,
                thread_summary="x",
            )


class TestCompilerNode:
    @patch("api.services.extraction.nodes.compiler._get_structured_llm")
    def test_successful_compilation(self, mock_get_llm, tech_thread, high_quality_article):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = ExtractedKnowledge(**high_quality_article)
        mock_get_llm.return_value = mock_llm

        state = {"threads": [tech_thread], "current_thread_idx": 0}
        result = compiler_node(state)

        assert result["compiled_article"] is not None
        assert result["compiled_article"]["language"] == "javascript"
        assert result["compiled_article"]["confidence"] == 0.92

    @patch("api.services.extraction.nodes.compiler._get_structured_llm")
    def test_llm_failure_returns_none(self, mock_get_llm, tech_thread):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("API error")
        mock_get_llm.return_value = mock_llm

        state = {"threads": [tech_thread], "current_thread_idx": 0}
        result = compiler_node(state)

        assert result["compiled_article"] is None
