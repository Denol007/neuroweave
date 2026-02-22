# LangGraph Extraction Pipeline

The core ML/AI pipeline that transforms raw Discord messages into structured knowledge articles.

## Graph Topology

```
START → disentangle → router →[NOISE→END | TECHNICAL→evaluator]
evaluator →[resolved→compiler | incomplete→END(checkpoint)]
compiler → quality_gate →[pass→END | retry→compiler | reject→END]
```

## Files

- `state.py` — AgentState TypedDict + helper types (ThreadMessage, EvaluationResult, CompiledArticle)
- `graph.py` — StateGraph assembly: add_node, add_edge, add_conditional_edges, compile
- `disentanglement.py` — Sentence-BERT clustering (NOT an LLM node)
- `nodes/router.py` — NOISE/TECHNICAL classification (Claude Haiku)
- `nodes/evaluator.py` — Resolution assessment + cyclic edge (Claude Haiku)
- `nodes/compiler.py` — Structured output with Pydantic via `with_structured_output()` (Claude Haiku)
- `nodes/quality_gate.py` — Heuristic scorer (NO LLM)

## AgentState Fields

```python
messages: list[BaseMessage]          # Raw input (Annotated with operator.add)
threads: list[list[ThreadMessage]]   # Clustered by disentanglement
classification: "NOISE"|"TECHNICAL"  # Router output
evaluation: EvaluationResult | None  # Evaluator output
compiled_article: CompiledArticle | None  # Compiler output
quality_score: float                 # Quality gate score (0.0-1.0)
retry_count: int                     # Compiler retry counter (max 3)
current_thread_idx: int              # Which thread is being processed
server_id: str                       # Discord server context
channel_id: str                      # Discord channel context
error: str | None                    # Error tracking
```

## LLM Configuration

All LLM nodes use:
- Model: `claude-haiku-4-5-20251001`
- Temperature: `0` (deterministic)
- Provider: `langchain-anthropic` (`ChatAnthropic`)

## Checkpointing

- **Dev:** `MemorySaver()` — in-memory, lost on restart
- **Prod:** `MongoDBSaver(connection_string, db_name="neuroweave", collection_name="checkpoints")`
- Thread ID format: `"discord_{channel_id}_{thread_hash}"`
- Enables cyclic re-evaluation: incomplete threads checkpoint, resume when new messages arrive

## Quality Gate Weights

| Factor | Max Weight |
|--------|-----------|
| Solution length (>200 chars) | 0.25 |
| Code snippet present (>50 chars) | 0.20 |
| LLM confidence | 0.20 |
| Tags coverage (>=5 tags) | 0.15 |
| Diagnosis meaningful (>80 chars) | 0.10 |
| Thread summary exists | 0.10 |
| **Threshold** | **0.70** |

## Disentanglement Parameters

- Model: `all-MiniLM-L6-v2` (384-dim embeddings)
- Similarity threshold: `0.75`
- Temporal window: `4 hours`
- Explicit links: reply_to, @mentions override similarity threshold
