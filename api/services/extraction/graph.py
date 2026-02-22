"""LangGraph StateGraph assembly for the extraction pipeline.

Graph topology:
  START → disentangle → router →[NOISE→END | TECHNICAL→evaluator]
  evaluator →[resolved→compiler | incomplete→END(checkpoint)]
  compiler → quality_gate →[pass→END | retry→compiler | reject→END]

Usage:
  graph = build_graph(use_mongodb=False)
  result = graph.invoke(initial_state, config={"configurable": {"thread_id": "ch_123"}})
"""

from __future__ import annotations

import os

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from api.services.extraction.disentanglement import DisentanglementEngine
from api.services.extraction.nodes.compiler import compiler_node
from api.services.extraction.nodes.evaluator import evaluator_node, route_after_evaluation
from api.services.extraction.nodes.quality_gate import quality_gate_node, route_after_quality
from api.services.extraction.nodes.router import route_after_classification, router_node
from api.services.extraction.state import AgentState

logger = structlog.get_logger()

# Shared disentanglement engine (loads Sentence-BERT once)
_disentangle_engine: DisentanglementEngine | None = None


def _get_disentangle_engine() -> DisentanglementEngine:
    global _disentangle_engine
    if _disentangle_engine is None:
        _disentangle_engine = DisentanglementEngine()
    return _disentangle_engine


def disentangle_node(state: AgentState) -> dict:
    """Pre-processing node: cluster raw messages into logical threads."""
    from api.services.extraction.disentanglement import RawMessage
    from datetime import datetime

    engine = _get_disentangle_engine()

    # Convert raw message dicts to RawMessage objects
    raw_messages = []
    for m in state["messages"]:
        raw_messages.append(RawMessage(
            id=m.get("id", ""),
            author_hash=m.get("author_hash", ""),
            content=m.get("content", ""),
            timestamp=datetime.fromisoformat(m["timestamp"]) if isinstance(m.get("timestamp"), str) else m.get("timestamp", datetime.now()),
            has_code="```" in m.get("content", ""),
            reply_to=m.get("reply_to"),
            mentions=m.get("mentions", []),
        ))

    threads = engine.cluster(raw_messages)

    # Convert back to ThreadMessage dicts
    thread_dicts = []
    for thread in threads:
        thread_msgs = []
        for msg in thread:
            thread_msgs.append({
                "author_hash": msg.author_hash,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
                "has_code": msg.has_code,
                "has_mention": bool(msg.mentions),
                "reply_to": msg.reply_to,
            })
        thread_dicts.append(thread_msgs)

    # Filter out empty/single-message threads and pick the largest
    thread_dicts = [t for t in thread_dicts if len(t) >= 2]

    if not thread_dicts:
        # If no multi-message threads, use all messages as one thread
        all_msgs = []
        for thread in threads:
            for msg in thread:
                all_msgs.append({
                    "author_hash": msg.author_hash,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "has_code": msg.has_code,
                    "has_mention": bool(msg.mentions),
                    "reply_to": msg.reply_to,
                })
        thread_dicts = [all_msgs] if all_msgs else []

    # Sort by size — process largest thread first
    thread_dicts.sort(key=len, reverse=True)

    return {
        "threads": thread_dicts,
        "current_thread_idx": 0,
    }


def build_graph(use_mongodb: bool = False):
    """Construct and compile the extraction pipeline graph.

    Args:
        use_mongodb: If True, use MongoDBSaver for persistent checkpoints.
                     If False, use MemorySaver (dev/testing).

    Returns:
        Compiled LangGraph app ready for .invoke() or .stream().
    """
    # 1. Initialize StateGraph with schema
    workflow = StateGraph(AgentState)

    # 2. Add nodes
    workflow.add_node("disentangle", disentangle_node)
    workflow.add_node("router", router_node)
    workflow.add_node("evaluator", evaluator_node)
    workflow.add_node("compiler", compiler_node)
    workflow.add_node("quality_gate", quality_gate_node)

    # 3. Set entry point
    workflow.set_entry_point("disentangle")

    # 4. Linear edges
    workflow.add_edge("disentangle", "router")
    workflow.add_edge("compiler", "quality_gate")

    # 5. Conditional edges
    workflow.add_conditional_edges(
        "router",
        route_after_classification,
        {"evaluator": "evaluator", "__end__": END},
    )
    workflow.add_conditional_edges(
        "evaluator",
        route_after_evaluation,
        {"compiler": "compiler", "__end__": END},
    )
    workflow.add_conditional_edges(
        "quality_gate",
        route_after_quality,
        {"compiler": "compiler", "__end__": END},
    )

    # 6. Select checkpointer
    if use_mongodb:
        from langgraph.checkpoint.mongodb import MongoDBSaver
        from pymongo import MongoClient

        mongo_client = MongoClient(os.environ.get("MONGODB_URI", "mongodb://localhost:27017"))
        checkpointer = MongoDBSaver(
            client=mongo_client,
            db_name="neuroweave",
            collection_name="checkpoints",
        )
    else:
        checkpointer = MemorySaver()

    # 7. Compile
    app = workflow.compile(checkpointer=checkpointer)

    logger.info("graph_compiled", checkpointer=type(checkpointer).__name__)
    return app
