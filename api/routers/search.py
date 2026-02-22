"""Search router — hybrid vector + full-text search.

Combines pgvector cosine similarity with PostgreSQL full-text search
for best-of-both-worlds ranking.

Endpoint:
  GET /api/search?q=...&server=...&language=...&limit=...
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import func, literal_column, select, text

from api.deps import DB
from api.models.article import Article
from api.models.channel import Channel
from api.models.thread import Thread
from api.schemas.article import ArticleBrief, SearchResponse, SearchResult
from api.services.embeddings import encode

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search_articles(
    db: DB,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    server: int | None = Query(None, description="Filter by server ID"),
    language: str | None = Query(None, description="Filter by language"),
    limit: int = Query(20, ge=1, le=100),
):
    """Hybrid search: combine vector similarity + full-text relevance.

    1. Generate embedding for the query text
    2. Compute cosine similarity against article embeddings (vector search)
    3. Compute full-text search rank using PostgreSQL ts_rank
    4. Combine scores: 0.6 * vector_score + 0.4 * fts_score
    5. Return top results sorted by combined score
    """
    # Generate query embedding
    query_embedding = encode(q).tolist()

    # Vector similarity score (1 - cosine distance = cosine similarity)
    vector_score = (
        literal_column("1") - Article.embedding.cosine_distance(query_embedding)
    ).label("vector_score")

    # Full-text search score
    ts_query = func.plainto_tsquery("english", q)
    fts_vector = func.to_tsvector(
        "english",
        func.concat(Article.thread_summary, " ", Article.symptom, " ", Article.solution),
    )
    fts_score = func.ts_rank(fts_vector, ts_query).label("fts_score")

    # Combined score
    combined_score = (literal_column("0.6") * vector_score + literal_column("0.4") * fts_score).label("score")

    # Build query
    query = (
        select(Article, combined_score)
        .where(Article.is_visible.is_(True))
        .where(Article.embedding.isnot(None))
    )

    # Optional filters
    if server:
        query = (
            query
            .join(Thread, Thread.id == Article.thread_id)
            .join(Channel, Channel.id == Thread.channel_id)
            .where(Channel.server_id == server)
        )
    if language:
        query = query.where(Article.language == language)

    query = query.order_by(text("score DESC")).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    search_results = []
    for row in rows:
        article = row[0]
        score = float(row[1]) if row[1] else 0.0
        search_results.append(
            SearchResult(
                article=ArticleBrief.model_validate(article),
                score=round(score, 4),
            )
        )

    return SearchResponse(
        results=search_results,
        query=q,
        total=len(search_results),
    )
