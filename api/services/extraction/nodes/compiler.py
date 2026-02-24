"""Compiler Node — transforms a thread into structured knowledge.

Adapts output based on article_type:
  TROUBLESHOOTING: symptom=error, diagnosis=root cause, solution=fix
  QUESTION_ANSWER: symptom=question, diagnosis=context, solution=answer
  GUIDE: symptom=topic, diagnosis=prerequisites, solution=guide content
  DISCUSSION_SUMMARY: symptom=topic, diagnosis=perspectives, solution=takeaways
"""

from __future__ import annotations

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from api.services.extraction.state import AgentState

logger = structlog.get_logger()

COMPILER_SYSTEM_PROMPT = """You are a knowledge compiler. Given a community discussion thread,
extract structured knowledge based on the article type.

ARTICLE TYPE: {article_type}

For TROUBLESHOOTING:
  - symptom: The exact error/problem (include error messages)
  - diagnosis: Root cause analysis
  - solution: Step-by-step fix
  - code_snippet: The code fix (null if none shared)

For QUESTION_ANSWER:
  - symptom: The question being asked
  - diagnosis: Context/background for the question
  - solution: The answer/explanation
  - code_snippet: Code example if any (null if none)

For GUIDE:
  - symptom: The topic/subject being explained
  - diagnosis: Prerequisites and context
  - solution: The full guide/tutorial content
  - code_snippet: Key code examples (null if none)

For DISCUSSION_SUMMARY:
  - symptom: The discussion topic
  - diagnosis: Key perspectives shared by participants
  - solution: Consensus, takeaways, or actionable insights
  - code_snippet: null (discussions rarely have code fixes)

RULES:
- language: Use the primary programming language, or "general" if no code involved
- tags: 3-7 lowercase kebab-case tags for discoverability
- confidence: 0.9+ clear/confirmed, 0.7-0.9 good but gaps, 0.5-0.7 uncertain
- Do NOT hallucinate. Only extract what was ACTUALLY discussed."""


class ExtractedKnowledge(BaseModel):
    """Pydantic schema for structured knowledge extraction."""

    article_type: str = Field(description="troubleshooting, question_answer, guide, or discussion_summary")
    symptom: str = Field(description="Problem, question, or topic")
    diagnosis: str = Field(description="Root cause, context, or background")
    solution: str = Field(description="Fix, answer, guide content, or takeaways")
    code_snippet: str | None = Field(default=None, description="Code fix or example, null if none")
    language: str = Field(default="general", description="Programming language or 'general'")
    framework: str | None = Field(default=None, description="Framework if applicable")
    tags: list[str] = Field(description="3-7 lowercase kebab-case tags")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence 0.0-1.0")
    thread_summary: str = Field(description="One-line summary for search (max 100 chars)")
    source_url: str | None = Field(default=None, description="URL to original discussion")


_structured_llm = None


def _get_structured_llm():
    global _structured_llm
    if _structured_llm is None:
        llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0, max_tokens=1500)
        _structured_llm = llm.with_structured_output(ExtractedKnowledge)
    return _structured_llm


def _format_thread(thread: list[dict]) -> str:
    lines = []
    for m in thread:
        author = m.get("author_hash", "???")[:8]
        ts = m.get("timestamp", "")
        content = m.get("content", "")
        lines.append(f"[{ts}] {author}: {content}")
    return "\n".join(lines)


def compiler_node(state: AgentState) -> dict:
    """Compile the current thread into structured knowledge."""
    thread = state["threads"][state["current_thread_idx"]]
    formatted = _format_thread(thread)
    article_type = state.get("article_type", "TROUBLESHOOTING").lower()

    prompt = COMPILER_SYSTEM_PROMPT.format(article_type=article_type.upper())
    structured_llm = _get_structured_llm()

    try:
        result: ExtractedKnowledge = structured_llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=f"Compile this thread:\n\n{formatted}"),
        ])
        compiled = result.model_dump()
        # Ensure article_type matches router classification
        compiled["article_type"] = article_type
        logger.info(
            "compiler_success",
            article_type=article_type,
            summary=compiled["thread_summary"][:80],
            confidence=compiled["confidence"],
            tags=compiled["tags"],
        )
    except Exception as e:
        logger.error("compiler_failed", error=str(e))
        compiled = None

    return {"compiled_article": compiled}
