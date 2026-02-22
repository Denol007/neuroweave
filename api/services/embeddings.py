"""Sentence-BERT embeddings wrapper.

Loads the model once at module level. Provides encode() for single texts
and encode_batch() for efficient batch processing.
"""

from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

# Model loaded once, reused across all calls
_model: SentenceTransformer | None = None

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def encode(text: str) -> np.ndarray:
    """Encode a single text into a 384-dim embedding vector."""
    model = _get_model()
    return model.encode(text, show_progress_bar=False)


def encode_batch(texts: list[str], batch_size: int = 64) -> np.ndarray:
    """Encode multiple texts into embedding vectors.

    Returns:
        np.ndarray of shape (len(texts), 384)
    """
    model = _get_model()
    return model.encode(texts, batch_size=batch_size, show_progress_bar=False)
