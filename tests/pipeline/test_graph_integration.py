"""Integration test: full pipeline graph with mocked LLM nodes."""

from unittest.mock import MagicMock, patch

from api.services.extraction.graph import build_graph
from api.services.extraction.nodes.compiler import ExtractedKnowledge


class TestGraphIntegration:
    """End-to-end tests with mocked LLM calls but real graph execution."""

    def _make_initial_state(self, messages):
        return {
            "messages": messages,
            "threads": [],
            "source_type": "discord",
            "skip_disentangle": False,
            "classification": "",
            "article_type": "",
            "evaluation": None,
            "compiled_article": None,
            "quality_score": 0.0,
            "retry_count": 0,
            "current_thread_idx": 0,
            "server_id": "test_server",
            "channel_id": "test_channel",
            "error": None,
        }

    def _sample_messages(self):
        return [
            {
                "id": "1", "author_hash": "ccc", "timestamp": "2026-02-22T14:02:00",
                "content": "Error: ENOMEM not enough memory during Next.js build\n```\nENOMEM\n```",
                "reply_to": None, "mentions": [],
            },
            {
                "id": "2", "author_hash": "ddd", "timestamp": "2026-02-22T14:04:00",
                "content": "Try setting workerThreads: false in next.config.js\n```js\nexperimental: { workerThreads: false }\n```",
                "reply_to": "1", "mentions": ["ccc"],
            },
            {
                "id": "3", "author_hash": "ccc", "timestamp": "2026-02-22T14:06:00",
                "content": "That fixed it! Thanks!",
                "reply_to": "2", "mentions": [],
            },
        ]

    @patch("api.services.extraction.nodes.compiler._get_structured_llm")
    @patch("api.services.extraction.nodes.evaluator._get_llm")
    @patch("api.services.extraction.nodes.router._get_llm")
    def test_full_pipeline_technical_resolved(
        self, mock_router_llm, mock_eval_llm, mock_compiler_llm
    ):
        """Technical thread → evaluator → compiler → quality gate → PASS."""
        # Mock Router: TROUBLESHOOTING
        router_llm = MagicMock()
        router_llm.invoke.return_value = MagicMock(content="TROUBLESHOOTING")
        mock_router_llm.return_value = router_llm

        # Mock Evaluator: resolved
        eval_llm = MagicMock()
        eval_llm.invoke.return_value = MagicMock(
            content='{"has_solution": true, "has_code": true, "is_resolved": true, "reasoning": "OP confirmed fix"}'
        )
        mock_eval_llm.return_value = eval_llm

        # Mock Compiler: high quality article
        article = ExtractedKnowledge(
            article_type="troubleshooting",
            symptom="Next.js 14 build fails with ENOMEM",
            diagnosis="Too many worker threads exhaust memory on constrained environments with limited RAM allocation",
            solution="Disable worker threads in next.config.js by setting experimental.workerThreads to false and limiting cpus to 2. Rebuild after changes.",
            code_snippet="experimental: { workerThreads: false, cpus: 2 }",
            language="javascript",
            framework="Next.js",
            tags=["next-js", "oom", "enomem", "build-error", "worker-threads"],
            confidence=0.9,
            thread_summary="Fix Next.js ENOMEM build error",
        )
        compiler_llm = MagicMock()
        compiler_llm.invoke.return_value = article
        mock_compiler_llm.return_value = compiler_llm

        # Run
        graph = build_graph(use_mongodb=False)
        state = self._make_initial_state(self._sample_messages())
        config = {"configurable": {"thread_id": "test_integration_1"}}

        result = graph.invoke(state, config=config)

        # Assertions
        assert result["classification"] == "TROUBLESHOOTING"
        assert result["evaluation"]["is_resolved"] is True
        assert result["compiled_article"] is not None
        assert result["compiled_article"]["language"] == "javascript"
        assert result["quality_score"] >= 0.7

    @patch("api.services.extraction.nodes.router._get_llm")
    def test_noise_filtered_early(self, mock_router_llm):
        """Noise thread → router → END (no evaluator/compiler calls)."""
        router_llm = MagicMock()
        router_llm.invoke.return_value = MagicMock(content="NOISE")
        mock_router_llm.return_value = router_llm

        messages = [
            {"id": "1", "author_hash": "a", "timestamp": "2026-02-22T14:00:00", "content": "gm gm", "reply_to": None, "mentions": []},
            {"id": "2", "author_hash": "b", "timestamp": "2026-02-22T14:00:30", "content": "hey!", "reply_to": None, "mentions": []},
        ]

        graph = build_graph(use_mongodb=False)
        state = self._make_initial_state(messages)
        config = {"configurable": {"thread_id": "test_noise_1"}}

        result = graph.invoke(state, config=config)

        assert result["classification"] == "NOISE"
        assert result["compiled_article"] is None
        assert result["quality_score"] == 0.0
