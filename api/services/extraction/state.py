"""AgentState schema for the LangGraph extraction pipeline.

This TypedDict flows through every node. Each node reads specific fields
and returns a dict with the fields it mutates.
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict


class ThreadMessage(TypedDict):
    """Single message within a disentangled thread."""

    author_hash: str       # SHA-256 of Discord user ID
    content: str           # PII-redacted message text
    timestamp: str         # ISO 8601 timestamp
    has_code: bool         # Contains code block (```)
    has_mention: bool      # Contains @mention
    reply_to: str | None   # Discord message ID of parent, if reply


class EvaluationResult(TypedDict):
    """Evaluator node output."""

    has_solution: bool     # Thread contains a proposed solution
    has_code: bool         # Solution includes code snippet
    is_resolved: bool      # Problem was confirmed resolved by OP
    reasoning: str         # LLM's evaluation reasoning


class CompiledArticle(TypedDict):
    """Compiler node structured output."""

    symptom: str
    diagnosis: str
    solution: str
    code_snippet: str | None
    language: str
    framework: str | None
    tags: list[str]
    confidence: float
    thread_summary: str


class AgentState(TypedDict):
    """Main state schema flowing through the LangGraph pipeline.

    Graph: disentangle → router → evaluator → compiler → quality_gate

    The `messages` field uses Annotated[list, operator.add] so that
    resuming from a checkpoint appends new messages to existing ones.
    """

    # --- Input ---
    messages: Annotated[list[dict], operator.add]
    threads: list[list[ThreadMessage]]

    # --- Router output ---
    classification: Literal["NOISE", "TECHNICAL", ""]

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
