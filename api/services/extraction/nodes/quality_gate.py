"""Quality Gate — heuristic scoring of compiled articles.

No LLM calls. Scores articles on 6 factors (max 1.0).
Articles must score >= 0.7 to pass. Failed articles retry
compilation up to 3 times before being rejected.

Score breakdown:
  Solution length (>200 chars)     0.25
  Code snippet present (>50 chars) 0.20
  LLM confidence                   0.20
  Tags coverage (>=5 tags)         0.15
  Diagnosis meaningful (>80 chars) 0.10
  Thread summary exists            0.10
  ─────────────────────────────────────
  THRESHOLD                        0.70
"""

from __future__ import annotations

import structlog

from api.services.extraction.state import AgentState

logger = structlog.get_logger()

QUALITY_THRESHOLD = 0.7
MAX_RETRIES = 3


def compute_quality_score(article: dict | None) -> float:
    """Compute heuristic quality score for a compiled article.

    Args:
        article: CompiledArticle dict or None.

    Returns:
        Score between 0.0 and 1.0.
    """
    if not article:
        return 0.0

    score = 0.0

    # Factor 1: Solution length (max 0.25)
    sol_len = len(article.get("solution", ""))
    if sol_len > 200:
        score += 0.25
    elif sol_len > 100:
        score += 0.15
    elif sol_len > 50:
        score += 0.08

    # Factor 2: Code snippet present (max 0.20)
    snippet = article.get("code_snippet")
    if snippet:
        snippet_len = len(snippet)
        if snippet_len > 50:
            score += 0.20
        else:
            score += 0.10

    # Factor 3: LLM confidence (max 0.20)
    confidence = article.get("confidence", 0.0)
    score += min(confidence * 0.20, 0.20)

    # Factor 4: Tags coverage (max 0.15)
    tags = article.get("tags", [])
    if len(tags) >= 5:
        score += 0.15
    elif len(tags) >= 3:
        score += 0.10
    elif len(tags) >= 1:
        score += 0.05

    # Factor 5: Diagnosis present and meaningful (max 0.10)
    diag_len = len(article.get("diagnosis", ""))
    if diag_len > 80:
        score += 0.10
    elif diag_len > 30:
        score += 0.05

    # Factor 6: Thread summary exists (max 0.10)
    if len(article.get("thread_summary", "")) > 10:
        score += 0.10

    return round(min(score, 1.0), 2)


def quality_gate_node(state: AgentState) -> dict:
    """Score the compiled article and update state."""
    article = state.get("compiled_article")
    score = compute_quality_score(article)
    retry_count = state.get("retry_count", 0)

    if score >= QUALITY_THRESHOLD:
        logger.info("quality_gate_pass", score=score)
    else:
        logger.warning(
            "quality_gate_fail",
            score=score,
            retry=retry_count + 1,
            max_retries=MAX_RETRIES,
        )

    return {
        "quality_score": score,
        "retry_count": retry_count + (1 if score < QUALITY_THRESHOLD else 0),
    }


def route_after_quality(state: AgentState) -> str:
    """Conditional edge: pass → end, retry → compiler, reject → end.

    - score >= 0.7: PASS — article is stored
    - score < 0.7 and retries < 3: RETRY — re-compile
    - score < 0.7 and retries >= 3: REJECT — give up
    """
    if state["quality_score"] >= QUALITY_THRESHOLD:
        return "__end__"
    if state["retry_count"] < MAX_RETRIES:
        return "compiler"
    logger.error("quality_gate_rejected", score=state["quality_score"], retries=state["retry_count"])
    return "__end__"
