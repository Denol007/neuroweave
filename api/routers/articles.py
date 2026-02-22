"""Articles router — knowledge base CRUD.

Endpoints:
  GET /api/servers/{server_id}/articles — list articles for a server
  GET /api/articles/{article_id}        — get single article
  PATCH /api/articles/{article_id}/moderate — hide/show article (admin)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from api.deps import DB, CurrentUser
from api.models.article import Article
from api.models.channel import Channel
from api.schemas.article import ArticleBrief, ArticleListResponse, ArticleResponse

router = APIRouter()


@router.get("/servers/{server_id}/articles", response_model=ArticleListResponse)
async def list_server_articles(
    server_id: int,
    db: DB,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    language: str | None = None,
    tag: str | None = None,
):
    """List articles for a server with optional filtering."""
    # Base query: articles joined through threads → channels → server
    base_query = (
        select(Article)
        .join(Article.thread)
        .join(Channel, Channel.id == Article.thread.property.mapper.class_.channel_id)
        .where(Channel.server_id == server_id)
        .where(Article.is_visible.is_(True))
    )

    if language:
        base_query = base_query.where(Article.language == language)
    if tag:
        base_query = base_query.where(Article.tags.any(tag))

    # Count total
    count_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = (
        base_query
        .order_by(Article.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    articles = result.scalars().all()

    return ArticleListResponse(
        items=[ArticleBrief.model_validate(a) for a in articles],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int, db: DB):
    """Get a single article by ID."""
    result = await db.execute(
        select(Article).where(Article.id == article_id, Article.is_visible.is_(True))
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    return ArticleResponse.model_validate(article)


@router.patch("/articles/{article_id}/moderate")
async def moderate_article(
    article_id: int,
    is_visible: bool,
    db: DB,
    user: CurrentUser,
):
    """Hide or show an article (admin only)."""
    result = await db.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    article.is_visible = is_visible
    return {"id": article_id, "is_visible": is_visible}
