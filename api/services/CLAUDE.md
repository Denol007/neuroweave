# API Services

Business logic layer. Each service encapsulates a domain capability.

## Services

- `anonymizer.py` — PII detection and redaction using Llama 3.2 1B (CPU inference)
- `embeddings.py` — Sentence-BERT wrapper for generating embeddings (all-MiniLM-L6-v2, 384-dim)
- `c2pa_signer.py` — C2PA digital provenance manifest creation and X.509 signing
- `dataset_packager.py` — JSONL export bundling for dataset marketplace

## Patterns

- Services are stateless classes or module-level functions
- All I/O is async
- Services receive database sessions via dependency injection, not global state
- Heavy ML models (Sentence-BERT, Llama) are loaded once at module level
