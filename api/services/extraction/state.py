"""AgentState schema for the LangGraph extraction pipeline.

This TypedDict flows through every node. Each node reads specific fields
and returns a dict with the fields it mutates.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

# Valid article type classifications
ARTICLE_TYPES = ("TROUBLESHOOTING", "QUESTION_ANSWER", "GUIDE", "DISCUSSION_SUMMARY")
NOISE_OR_ARTICLE = ("NOISE", *ARTICLE_TYPES)


class ThreadMessage(TypedDict):
    """Single message within a disentangled thread."""

    author_hash: str       # SHA-256 of user ID
    content: str           # PII-redacted message text
    timestamp: str         # ISO 8601 timestamp
    has_code: bool         # Contains code block
    has_mention: bool      # Contains @mention
    reply_to: str | None   # Parent message ID, if reply


class EvaluationResult(TypedDict):
    """Evaluator node output."""

    has_solution: bool     # Thread contains a proposed solution/answer
    has_code: bool         # Solution includes code snippet
    is_resolved: bool      # Problem was confirmed resolved
    reasoning: str         # LLM evaluation reasoning


class CompiledArticle(TypedDict):
    """Compiler node structured output."""

    article_type: str           # troubleshooting, question_answer, guide, discussion_summary
    symptom: str                # Problem/question/topic
    diagnosis: str              # Root cause/context/background
    solution: str               # Solution/answer/guide content
    code_snippet: str | None
    language: str               # "python", "javascript", or "general" for non-code
    framework: str | None
    tags: list[str]
    confidence: float
    thread_summary: str
    source_url: str | None


class AgentState(TypedDict):
    """Main state schema flowing through the LangGraph pipeline."""

    # --- Input ---
    messages: Annotated[list[dict], operator.add]
    threads: list[list[ThreadMessage]]

    # --- Source context ---
    source_type: str               # "discord", "github", "discourse"
    skip_disentangle: bool         # True for pre-threaded sources (GitHub)

    # --- Router output ---
    classification: str            # NOISE, TROUBLESHOOTING, QUESTION_ANSWER, GUIDE, DISCUSSION_SUMMARY
    article_type: str              # Same as classification (minus NOISE)

    # --- Evaluator output ---
    evaluation: EvaluationResult | None

    # --- Compiler output ---
    compiled_article: CompiledArticle | None

    # --- Quality gate ---
    quality_score: float
    retry_count: int

    # --- Context ---
    current_thread_idx: int
    server_id: str
    channel_id: str
    error: str | None
