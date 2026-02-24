"""Evaluator Node — assesses whether a thread has enough substance to compile.

Article-type-aware routing:
  TROUBLESHOOTING: needs has_solution + (has_code OR is_resolved)
  QUESTION_ANSWER: needs has_solution (code optional)
  GUIDE / DISCUSSION_SUMMARY: always passes (inherently complete)
"""

from __future__ import annotations

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from api.services.extraction.state import AgentState, EvaluationResult

EVALUATOR_SYSTEM_PROMPT = """You are evaluating a community discussion thread.

Analyze the thread and determine:
1. has_solution: Does anyone provide a concrete answer, solution, or explanation?
2. has_code: Is there a code snippet, config change, or command?
3. is_resolved: Did the original poster confirm it helped or is the answer clearly correct?
4. reasoning: Brief explanation (2-3 sentences).

Respond with ONLY a JSON object:
{
  "has_solution": true/false,
  "has_code": true/false,
  "is_resolved": true/false,
  "reasoning": "Brief explanation"
}"""

_llm: ChatAnthropic | None = None


def _get_llm() -> ChatAnthropic:
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0, max_tokens=300)
    return _llm


def _format_thread(thread: list[dict]) -> str:
    lines = []
    for m in thread:
        author = m.get("author_hash", "???")[:8]
        ts = m.get("timestamp", "")
        content = m.get("content", "")
        lines.append(f"[{ts}] {author}: {content}")
    return "\n".join(lines)


def _parse_evaluation(content: str) -> EvaluationResult:
    text = content.strip()
    if "```" in text:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
    try:
        data = json.loads(text)
        return EvaluationResult(
            has_solution=bool(data.get("has_solution", False)),
            has_code=bool(data.get("has_code", False)),
            is_resolved=bool(data.get("is_resolved", False)),
            reasoning=str(data.get("reasoning", "")),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return EvaluationResult(
            has_solution=False, has_code=False, is_resolved=False,
            reasoning=f"Failed to parse LLM response: {content[:200]}",
        )


def evaluator_node(state: AgentState) -> dict:
    """Evaluate whether the current thread has enough substance."""
    thread = state["threads"][state["current_thread_idx"]]
    formatted = _format_thread(thread)
    llm = _get_llm()
    response = llm.invoke([
        SystemMessage(content=EVALUATOR_SYSTEM_PROMPT),
        HumanMessage(content=f"Evaluate this thread:\n\n{formatted}"),
    ])
    evaluation = _parse_evaluation(response.content)
    return {"evaluation": evaluation}


def route_after_evaluation(state: AgentState) -> str:
    """Article-type-aware routing to compiler or checkpoint.

    TROUBLESHOOTING: needs solution + (code or resolution)
    QUESTION_ANSWER: needs solution (code optional)
    GUIDE / DISCUSSION_SUMMARY: always proceed
    """
    evaluation = state.get("evaluation")
    if not evaluation:
        return "__end__"

    article_type = state.get("article_type", "TROUBLESHOOTING")

    # GUIDE and DISCUSSION_SUMMARY always proceed — inherently complete
    if article_type in ("GUIDE", "DISCUSSION_SUMMARY"):
        return "compiler"

    # QUESTION_ANSWER: needs a solution, code is optional
    if article_type == "QUESTION_ANSWER":
        if evaluation["has_solution"]:
            return "compiler"
        return "__end__"

    # TROUBLESHOOTING: needs solution + (code or explicit resolution)
    if evaluation["is_resolved"] and evaluation["has_code"]:
        return "compiler"
    if evaluation["has_solution"] and evaluation["has_code"]:
        return "compiler"
    if evaluation["has_solution"] and evaluation["is_resolved"]:
        return "compiler"

    return "__end__"
