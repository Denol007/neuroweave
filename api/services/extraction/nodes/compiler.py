"""Compiler Node — transforms a resolved thread into structured knowledge.

Uses Claude Haiku with Pydantic schema enforcement via
`with_structured_output()`. The LLM generates a tool call matching
the ExtractedKnowledge schema, which LangChain parses and validates.

On validation failure, returns None so the quality gate triggers a retry.
"""

from __future__ import annotations

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from api.services.extraction.state import AgentState

logger = structlog.get_logger()

COMPILER_SYSTEM_PROMPT = """You are a technical knowledge compiler.

Given a Discord conversation thread where a technical problem was discussed
and resolved, extract structured knowledge.

RULES:
1. SYMPTOM: Write as if you're the person who had the problem. Include the
   exact error message if present. Be specific — not "app crashes" but
   "Next.js 14 build fails with ENOMEM error when running next build".

2. DIAGNOSIS: Explain the ROOT CAUSE technically. Why did this happen?
   What mechanism caused the failure?

3. SOLUTION: Step-by-step instructions someone can follow. Number the steps.
   Include prerequisites if any.

4. CODE_SNIPPET: Extract the EXACT fix from the conversation. If multiple
   snippets, combine into one coherent block. Add brief comments.
   If no code was shared, set to null — do NOT invent code.

5. TAGS: 3-7 tags. Include: language, framework, error type, affected
   component. Use lowercase kebab-case: "next-js" not "Next.js".

6. CONFIDENCE: Your honest assessment:
   - 0.9+: Clear problem, clear solution, confirmed working
   - 0.7-0.9: Good solution but minor gaps
   - 0.5-0.7: Solution seems right but not fully verified
   - Below 0.5: Uncertain

CRITICAL: Do NOT hallucinate. Only extract what was ACTUALLY discussed.
If a code snippet is incomplete, include it as-is with a comment."""


class ExtractedKnowledge(BaseModel):
    """Pydantic schema for structured knowledge extraction.

    This schema is passed to Claude via with_structured_output(),
    which converts it to a tool definition for guaranteed structured responses.
    """

    symptom: str = Field(
        description="The problem or error the user encountered. Include exact error messages."
    )
    diagnosis: str = Field(
        description="Root cause analysis — why the problem happened technically."
    )
    solution: str = Field(
        description="Step-by-step solution that resolved the issue."
    )
    code_snippet: str | None = Field(
        default=None,
        description="Relevant code fix, config change, or CLI command. Null if no code was shared.",
    )
    language: str = Field(
        description="Primary programming language: python, javascript, rust, go, etc."
    )
    framework: str | None = Field(
        default=None,
        description="Framework if applicable: Next.js, Django, Tokio, etc.",
    )
    tags: list[str] = Field(
        description="3-7 lowercase kebab-case tags for search and filtering."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the extracted knowledge (0.0-1.0).",
    )
    thread_summary: str = Field(
        description="One-line summary for search results (max 100 chars)."
    )


_structured_llm = None


def _get_structured_llm():
    global _structured_llm
    if _structured_llm is None:
        llm = ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            temperature=0,
            max_tokens=1500,
        )
        _structured_llm = llm.with_structured_output(ExtractedKnowledge)
    return _structured_llm


def _format_thread(thread: list[dict]) -> str:
    """Format a thread's messages for the LLM prompt."""
    lines = []
    for m in thread:
        author = m.get("author_hash", "???")[:8]
        ts = m.get("timestamp", "")
        content = m.get("content", "")
        lines.append(f"[{ts}] {author}: {content}")
    return "\n".join(lines)


def compiler_node(state: AgentState) -> dict:
    """Compile the current thread into structured ExtractedKnowledge."""
    thread = state["threads"][state["current_thread_idx"]]
    formatted = _format_thread(thread)

    structured_llm = _get_structured_llm()

    try:
        result: ExtractedKnowledge = structured_llm.invoke([
            SystemMessage(content=COMPILER_SYSTEM_PROMPT),
            HumanMessage(content=f"Compile this resolved thread into structured knowledge:\n\n{formatted}"),
        ])
        compiled = result.model_dump()
        logger.info(
            "compiler_success",
            summary=compiled["thread_summary"][:80],
            confidence=compiled["confidence"],
            tags=compiled["tags"],
        )
    except Exception as e:
        logger.error("compiler_failed", error=str(e))
        compiled = None

    return {"compiled_article": compiled}
