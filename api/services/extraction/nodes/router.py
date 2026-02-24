"""Router Node — classifies threads into content categories.

Categories:
  NOISE — spam, greetings, off-topic (discarded)
  TROUBLESHOOTING — error + diagnosis + fix (code involved)
  QUESTION_ANSWER — "How do I X?" with answer (code optional)
  GUIDE — tutorial, walkthrough, architectural explanation
  DISCUSSION_SUMMARY — general discussion with valuable insights
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from api.services.extraction.state import AgentState, ARTICLE_TYPES

ROUTER_SYSTEM_PROMPT = """You are a community discussion classifier. Analyze a conversation thread and classify it.

Categories:
- NOISE: spam, greetings, off-topic chat, memes, bot commands, self-promotion
- TROUBLESHOOTING: error/bug report with debugging discussion and fix (usually has code/stack traces)
- QUESTION_ANSWER: "How do I...?" question with a clear answer (code is optional)
- GUIDE: tutorial, walkthrough, architectural explanation, or step-by-step instructions
- DISCUSSION_SUMMARY: general discussion with valuable insights, multiple perspectives, but no single answer

Rules:
- If the thread has stack traces, error messages, or debugging → TROUBLESHOOTING
- If someone asks "How to..." and gets a direct answer → QUESTION_ANSWER
- If it reads like a tutorial or explanation → GUIDE
- If multiple people share opinions/experiences with no single answer → DISCUSSION_SUMMARY
- Greetings, jokes, < 2 substantive messages → NOISE
- When uncertain, classify as QUESTION_ANSWER (broadest useful category)

Respond with JSON: {"classification": "CATEGORY", "reason": "one sentence"}"""

_llm: ChatAnthropic | None = None


def _get_llm() -> ChatAnthropic:
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0, max_tokens=150)
    return _llm


def _format_thread(thread: list[dict]) -> str:
    lines = []
    for m in thread:
        author = m.get("author_hash", "???")[:8]
        ts = m.get("timestamp", "")
        content = m.get("content", "")
        lines.append(f"[{ts}] {author}: {content}")
    return "\n".join(lines)


def router_node(state: AgentState) -> dict:
    """Classify the current thread into a content category."""
    thread = state["threads"][state["current_thread_idx"]]
    formatted = _format_thread(thread)

    llm = _get_llm()
    response = llm.invoke([
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=f"Classify this thread:\n\n{formatted}"),
    ])

    text = response.content.strip().upper()

    # Match against known categories
    classification = "QUESTION_ANSWER"  # default: broadest useful category
    for cat in ("NOISE", *ARTICLE_TYPES):
        if cat in text:
            classification = cat
            break

    article_type = classification if classification != "NOISE" else ""

    return {"classification": classification, "article_type": article_type}


def route_after_classification(state: AgentState) -> str:
    """Conditional edge: NOISE → end, everything else → evaluator."""
    if state["classification"] == "NOISE":
        return "__end__"
    return "evaluator"
