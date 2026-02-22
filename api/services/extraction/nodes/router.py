"""Router Node — classifies threads as NOISE or TECHNICAL.

Uses Claude Haiku with zero-shot prompting. When uncertain,
defaults to TECHNICAL (false positives are filtered downstream
by the quality gate; false negatives lose knowledge forever).
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from api.services.extraction.state import AgentState

ROUTER_SYSTEM_PROMPT = """You are a Discord message classifier for a technical community.

Your job: classify a conversation thread as either NOISE or TECHNICAL.

NOISE = greetings, memes, off-topic chat, emoji spam, bot commands,
        self-promotion, messages with no technical substance.
        Threads with < 3 messages AND no code/errors are likely NOISE.

TECHNICAL = questions about code, error messages, stack traces,
            configuration issues, architecture discussions,
            bug reports, code reviews, deployment problems.
            Any thread with a code block or stack trace is TECHNICAL.

EDGE CASES (classify as TECHNICAL):
- "Same issue here" with prior technical context → TECHNICAL
- Questions without answers (still valuable) → TECHNICAL
- "How do I..." about programming → TECHNICAL

EDGE CASES (classify as NOISE):
- "What IDE do you use?" preference polls → NOISE
- General career advice without code → NOISE

IMPORTANT: When uncertain, classify as TECHNICAL.
False positives are cheap (filtered later). False negatives lose knowledge forever.

Respond with a JSON object: {"classification": "NOISE" or "TECHNICAL", "reason": "one sentence"}"""

_llm: ChatAnthropic | None = None


def _get_llm() -> ChatAnthropic:
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(
            model="claude-haiku-4-5-20251001",
            temperature=0,
            max_tokens=100,
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


def router_node(state: AgentState) -> dict:
    """Classify the current thread as NOISE or TECHNICAL."""
    thread = state["threads"][state["current_thread_idx"]]
    formatted = _format_thread(thread)

    llm = _get_llm()
    response = llm.invoke([
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=f"Classify this thread:\n\n{formatted}"),
    ])

    # Parse response — extract classification
    text = response.content.strip().upper()

    if "NOISE" in text and "TECHNICAL" not in text:
        classification = "NOISE"
    elif "TECHNICAL" in text:
        classification = "TECHNICAL"
    else:
        # Default: false positive is cheaper than false negative
        classification = "TECHNICAL"

    return {"classification": classification}


def route_after_classification(state: AgentState) -> str:
    """Conditional edge: NOISE → end, TECHNICAL → evaluator."""
    if state["classification"] == "NOISE":
        return "__end__"
    return "evaluator"
