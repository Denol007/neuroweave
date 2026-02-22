"""Evaluator Node — assesses whether a technical thread contains a resolved solution.

Uses Claude Haiku to analyze threads. Returns structured evaluation:
has_solution, has_code, is_resolved, reasoning.

Supports cyclic re-evaluation: if the thread is not resolved, the graph
checkpoints and can resume when new messages arrive.
"""

from __future__ import annotations

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from api.services.extraction.state import AgentState, EvaluationResult

EVALUATOR_SYSTEM_PROMPT = """You are evaluating a technical Discord conversation thread.

Analyze the thread and determine:
1. has_solution: Does anyone propose a concrete solution?
2. has_code: Is there a code snippet, config change, or CLI command in the solution?
3. is_resolved: Did the original poster confirm it works, or is the solution clearly correct?
4. reasoning: Brief explanation of your assessment (2-3 sentences).

RESOLUTION SIGNALS (strong → weak):
1. STRONGEST: OP says "that worked", "fixed it", "thanks, solved"
2. STRONG: OP reacts positively to a solution message
3. MODERATE: Detailed solution with steps + code + explanation, no OP confirmation
4. WEAK: Someone proposes a fix but no confirmation
5. NONE: Only questions, no proposed solutions

RULES:
- is_resolved = true ONLY for signals 1-2 (explicit OP confirmation)
- is_resolved = false for signals 3-5 (we don't assume)
- If OP disappears after a solution is posted → is_resolved = false
- "Solved it myself" without sharing how → has_solution = false

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
        _llm = ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            temperature=0,
            max_tokens=300,
        )
    return _llm


def _format_thread(thread: list[dict]) -> str:
    """Format a thread's messages for the LLM prompt."""
    lines = []
    for m in thread:
        author = m.get("author_hash", "???")[:8]
        ts = m.get("timestamp", "")
        content = m.get("content", "")
        lines.append(f"[{ts}] {author}: {content}")
    return "\n".join(lines)


def _parse_evaluation(content: str) -> EvaluationResult:
    """Parse LLM response into EvaluationResult. Handles malformed JSON gracefully."""
    # Try to extract JSON from the response
    text = content.strip()

    # Handle markdown code blocks
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
            has_solution=False,
            has_code=False,
            is_resolved=False,
            reasoning=f"Failed to parse LLM response: {content[:200]}",
        )


def evaluator_node(state: AgentState) -> dict:
    """Evaluate whether the current thread has a complete resolution."""
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
    """Conditional edge: resolved → compiler, not resolved → end (checkpoint).

    The graph ends when not resolved, but the state is persisted via
    checkpointer. When new messages arrive, the graph resumes from
    the checkpoint with updated threads, and the evaluator re-runs.
    """
    evaluation = state.get("evaluation")
    if not evaluation:
        return "__end__"

    # Confirmed resolved with code → proceed to compiler
    if evaluation["is_resolved"] and evaluation["has_code"]:
        return "compiler"

    # Has a good solution even without explicit confirmation
    # (high-signal: has_solution + has_code = likely useful)
    if evaluation["has_solution"] and evaluation["has_code"]:
        return "compiler"

    # Everything else: checkpoint and wait
    return "__end__"
