"""Quality Gate — article-type-aware heuristic scoring.

Score breakdown varies by article type:
  TROUBLESHOOTING: code_snippet worth 0.20 (original behavior)
  QUESTION_ANSWER: code weight redistributed to solution length
  GUIDE: code weight redistributed to solution length
  DISCUSSION_SUMMARY: code weight redistributed to diagnosis (perspectives)

Threshold: 0.70 for all types. Max 3 retries.
"""

from __future__ import annotations

import structlog

from api.services.extraction.state import AgentState

logger = structlog.get_logger()

QUALITY_THRESHOLD = 0.7
MAX_RETRIES = 3


def compute_quality_score(article: dict | None) -> float:
    """Compute article-type-aware quality score. Returns 0.0-1.0."""
    if not article:
        return 0.0

    article_type = article.get("article_type", "troubleshooting").upper()
    score = 0.0

    sol_len = len(article.get("solution", ""))
    diag_len = len(article.get("diagnosis", ""))
    snippet = article.get("code_snippet")
    snippet_len = len(snippet) if snippet else 0
    confidence = article.get("confidence", 0.0)
    tags = article.get("tags", [])
    summary = article.get("thread_summary", "")

    if article_type == "TROUBLESHOOTING":
        # Original weights — code is important
        if sol_len > 200: score += 0.25
        elif sol_len > 100: score += 0.15
        elif sol_len > 50: score += 0.08

        if snippet_len > 50: score += 0.20
        elif snippet_len > 0: score += 0.10

        score += min(confidence * 0.20, 0.20)

        if len(tags) >= 5: score += 0.15
        elif len(tags) >= 3: score += 0.10
        elif len(tags) >= 1: score += 0.05

        if diag_len > 80: score += 0.10
        elif diag_len > 30: score += 0.05

        if len(summary) > 10: score += 0.10

    else:
        # QUESTION_ANSWER, GUIDE, DISCUSSION_SUMMARY
        # Code is optional — redistribute 0.20 code weight to solution/diagnosis

        # Solution length (max 0.35 — boosted from 0.25)
        if sol_len > 200: score += 0.35
        elif sol_len > 100: score += 0.25
        elif sol_len > 50: score += 0.15

        # Confidence (max 0.20)
        score += min(confidence * 0.20, 0.20)

        # Tags (max 0.15)
        if len(tags) >= 5: score += 0.15
        elif len(tags) >= 3: score += 0.10
        elif len(tags) >= 1: score += 0.05

        # Diagnosis / context (max 0.15 — boosted from 0.10)
        if diag_len > 80: score += 0.15
        elif diag_len > 30: score += 0.08

        # Summary (max 0.10)
        if len(summary) > 10: score += 0.10

        # Bonus: code present even though not required (max 0.05)
        if snippet_len > 50: score += 0.05

    return round(min(score, 1.0), 2)


def quality_gate_node(state: AgentState) -> dict:
    """Score the compiled article and update state."""
    article = state.get("compiled_article")
    score = compute_quality_score(article)
    retry_count = state.get("retry_count", 0)

    if score >= QUALITY_THRESHOLD:
        logger.info("quality_gate_pass", score=score, article_type=state.get("article_type"))
    else:
        logger.warning("quality_gate_fail", score=score, retry=retry_count + 1)

    return {
        "quality_score": score,
        "retry_count": retry_count + (1 if score < QUALITY_THRESHOLD else 0),
    }


def route_after_quality(state: AgentState) -> str:
    """pass → end, retry → compiler, reject → end."""
    if state["quality_score"] >= QUALITY_THRESHOLD:
        return "__end__"
    if state["retry_count"] < MAX_RETRIES:
        return "compiler"
    logger.error("quality_gate_rejected", score=state["quality_score"], retries=state["retry_count"])
    return "__end__"
