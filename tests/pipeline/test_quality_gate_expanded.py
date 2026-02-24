"""Tests for expanded Quality Gate — type-aware scoring."""

from api.services.extraction.nodes.quality_gate import QUALITY_THRESHOLD, compute_quality_score


class TestQualityGateTypeAware:
    def test_qa_no_code_passes(self):
        """Q&A article without code should pass quality gate."""
        article = {
            "article_type": "question_answer",
            "symptom": "How to structure a large monorepo project with multiple teams?",
            "diagnosis": "As projects grow, teams need clear boundaries for code ownership and independent deployments without conflicts.",
            "solution": "Use Turborepo with packages/ for each team. Shared UI in packages/ui. Apps in apps/. Route groups for organization. Path aliases for clean imports.",
            "code_snippet": None,
            "language": "general",
            "tags": ["architecture", "monorepo", "team-structure", "turborepo", "organization"],
            "confidence": 0.85,
            "thread_summary": "Structure large projects with Turborepo monorepo",
        }
        score = compute_quality_score(article)
        assert score >= QUALITY_THRESHOLD, f"Q&A without code scored {score}, expected >= {QUALITY_THRESHOLD}"

    def test_guide_no_code_passes(self):
        """Guide article without code should pass."""
        article = {
            "article_type": "guide",
            "symptom": "Understanding authentication patterns in modern web apps",
            "diagnosis": "Multiple auth approaches exist: JWT, sessions, OAuth2. Each has tradeoffs for security, scalability, and UX.",
            "solution": "For most apps, use OAuth2 with a provider like Auth0 or Clerk. Store tokens in httpOnly cookies. Use middleware for route protection. For SPAs, use the BFF pattern to avoid token exposure in the browser.",
            "code_snippet": None,
            "language": "general",
            "tags": ["authentication", "oauth2", "jwt", "security", "web-development"],
            "confidence": 0.82,
            "thread_summary": "Authentication patterns for modern web apps",
        }
        score = compute_quality_score(article)
        assert score >= QUALITY_THRESHOLD, f"Guide scored {score}"

    def test_discussion_summary_passes(self):
        """Discussion summary should pass with good content."""
        article = {
            "article_type": "discussion_summary",
            "symptom": "What's the best state management approach in 2026?",
            "diagnosis": "Redux, Zustand, Jotai, and server components all have vocal supporters. The discussion revealed nuanced tradeoffs between bundle size, DX, and server/client boundaries.",
            "solution": "Consensus: use React Server Components for server state, Zustand for simple client state, and TanStack Query for async data. Redux is best for complex client-heavy apps with time-travel debugging needs.",
            "code_snippet": None,
            "language": "general",
            "tags": ["state-management", "react", "zustand", "redux", "server-components"],
            "confidence": 0.78,
            "thread_summary": "State management in 2026: consensus on RSC + Zustand + TanStack Query",
        }
        score = compute_quality_score(article)
        assert score >= QUALITY_THRESHOLD, f"Discussion scored {score}"

    def test_troubleshooting_with_code_still_works(self):
        """Existing troubleshooting articles should still score well."""
        article = {
            "article_type": "troubleshooting",
            "symptom": "Next.js build fails with ENOMEM error",
            "diagnosis": "Worker threads exhaust memory on constrained environments with limited RAM allocation for build processes",
            "solution": "Disable worker threads and limit CPUs in next.config.js experimental section to reduce memory usage during builds.",
            "code_snippet": "// next.config.js\nmodule.exports = { experimental: { workerThreads: false, cpus: 2 } }",
            "language": "javascript",
            "tags": ["next-js", "oom", "enomem", "build-error", "worker-threads"],
            "confidence": 0.9,
            "thread_summary": "Fix ENOMEM build error",
        }
        score = compute_quality_score(article)
        assert score >= QUALITY_THRESHOLD, f"Troubleshooting scored {score}"

    def test_troubleshooting_without_code_penalized(self):
        """Troubleshooting without code should score lower than with code."""
        with_code = {
            "article_type": "troubleshooting",
            "solution": "x" * 201,
            "code_snippet": "x" * 51,
            "diagnosis": "x" * 81,
            "tags": ["a", "b", "c", "d", "e"],
            "confidence": 0.9,
            "thread_summary": "fix something important",
        }
        without_code = {**with_code, "code_snippet": None}

        score_with = compute_quality_score(with_code)
        score_without = compute_quality_score(without_code)
        assert score_with > score_without, "Troubleshooting with code should score higher"

    def test_qa_code_bonus(self):
        """Q&A with code should get a small bonus."""
        base = {
            "article_type": "question_answer",
            "solution": "x" * 201,
            "diagnosis": "x" * 81,
            "tags": ["a", "b", "c", "d", "e"],
            "confidence": 0.9,
            "thread_summary": "answer a question",
            "code_snippet": None,
        }
        with_code = {**base, "code_snippet": "x" * 51}

        score_base = compute_quality_score(base)
        score_bonus = compute_quality_score(with_code)
        assert score_bonus > score_base, "Q&A with code should get bonus"
        assert score_bonus - score_base <= 0.06, "Bonus should be small (0.05)"
