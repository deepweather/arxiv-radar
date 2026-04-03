"""Hybrid search combining pgvector semantic search with PostgreSQL full-text search."""

from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import RRF_K
from app.services.embeddings import _get_model
from app.services.serializers import paper_row_to_dict


async def hybrid_search(
    db: AsyncSession,
    query: str,
    limit: int = 25,
    offset: int = 0,
    days: int | None = None,
    categories: list[str] | None = None,
    sort: str | None = None,
    user_id: str | None = None,
) -> list[dict]:
    """
    Merge semantic vector search and full-text search results
    using Reciprocal Rank Fusion (RRF).
    
    sort options: relevance (default), newest, oldest
    user_id: if provided, excludes papers the user has tagged
    """
    time_filter = ""
    params: dict = {"limit": limit * 3}

    if days:
        time_filter = "AND published_at > NOW() - make_interval(days => :days)"
        params["days"] = days

    cat_filter = ""
    if categories:
        cat_filter = "AND categories && :cats"
        params["cats"] = categories

    exclude_tagged_filter = ""
    if user_id:
        exclude_tagged_filter = """AND id NOT IN (
            SELECT pt.paper_id FROM paper_tags pt
            JOIN tags t ON t.id = pt.tag_id
            WHERE t.user_id = CAST(:user_id AS uuid)
        )"""
        params["user_id"] = user_id

    base_where = f"1=1 {time_filter} {cat_filter} {exclude_tagged_filter}"

    model = _get_model()
    query_embedding = model.encode([query], normalize_embeddings=True)[0]
    params["query_emb"] = str(query_embedding.tolist())

    vector_sql = text(f"""
        SELECT id, title, summary, authors, categories, pdf_url, published_at, updated_at,
               1 - (embedding <=> CAST(:query_emb AS vector)) AS semantic_score
        FROM papers
        WHERE embedding IS NOT NULL AND {base_where}
        ORDER BY embedding <=> CAST(:query_emb AS vector)
        LIMIT :limit
    """)
    vector_result = await db.execute(vector_sql, params)
    vector_rows = vector_result.fetchall()

    params["query_text"] = query
    fts_sql = text(f"""
        SELECT id, title, summary, authors, categories, pdf_url, published_at, updated_at,
               ts_rank_cd(tsv, plainto_tsquery('english', :query_text)) AS fts_score
        FROM papers
        WHERE tsv @@ plainto_tsquery('english', :query_text) AND {base_where}
        ORDER BY fts_score DESC
        LIMIT :limit
    """)
    fts_result = await db.execute(fts_sql, params)
    fts_rows = fts_result.fetchall()

    scores: dict[str, float] = defaultdict(float)
    paper_data: dict[str, dict] = {}

    for rank, row in enumerate(vector_rows):
        scores[row.id] += 1.0 / (RRF_K + rank + 1)
        paper_data[row.id] = paper_row_to_dict(row)

    for rank, row in enumerate(fts_rows):
        scores[row.id] += 1.0 / (RRF_K + rank + 1)
        if row.id not in paper_data:
            paper_data[row.id] = paper_row_to_dict(row)

    if sort == "newest":
        sorted_ids = sorted(paper_data.keys(), key=lambda pid: paper_data[pid].get("published_at") or "", reverse=True)
    elif sort == "oldest":
        sorted_ids = sorted(paper_data.keys(), key=lambda pid: paper_data[pid].get("published_at") or "")
    else:
        sorted_ids = sorted(scores.keys(), key=lambda pid: scores[pid], reverse=True)

    results = []
    for pid in sorted_ids[offset : offset + limit]:
        entry = paper_data[pid]
        entry["score"] = round(scores[pid], 6)
        results.append(entry)

    return results


async def list_papers(
    db: AsyncSession,
    limit: int = 25,
    offset: int = 0,
    days: int | None = None,
    categories: list[str] | None = None,
    sort: str | None = None,
    user_id: str | None = None,
) -> list[dict]:
    """List papers ordered by recency (default) or specified sort order.
    
    user_id: if provided, excludes papers the user has tagged
    """
    params: dict = {"limit": limit, "offset": offset}
    filters = []

    if days:
        filters.append("published_at > NOW() - make_interval(days => :days)")
        params["days"] = days
    if categories:
        filters.append("categories && :cats")
        params["cats"] = categories
    if user_id:
        filters.append("""id NOT IN (
            SELECT pt.paper_id FROM paper_tags pt
            JOIN tags t ON t.id = pt.tag_id
            WHERE t.user_id = CAST(:user_id AS uuid)
        )""")
        params["user_id"] = user_id

    where = " AND ".join(filters) if filters else "1=1"
    
    order_by = "published_at DESC"
    if sort == "oldest":
        order_by = "published_at ASC"
    elif sort == "newest":
        order_by = "published_at DESC"
    elif sort == "random":
        order_by = "RANDOM()"

    sql = text(f"""
        SELECT id, title, summary, authors, categories, pdf_url, published_at, updated_at
        FROM papers
        WHERE {where}
        ORDER BY {order_by}
        LIMIT :limit OFFSET :offset
    """)
    result = await db.execute(sql, params)
    return [paper_row_to_dict(row) for row in result.fetchall()]


async def get_paper(db: AsyncSession, paper_id: str) -> dict | None:
    """Fetch a single paper by arXiv ID."""
    sql = text("""
        SELECT id, title, summary, authors, categories, pdf_url, published_at, updated_at
        FROM papers WHERE id = :id
    """)
    result = await db.execute(sql, {"id": paper_id})
    row = result.fetchone()
    return paper_row_to_dict(row) if row else None


async def count_papers(db: AsyncSession) -> int:
    """Return total number of papers in the database."""
    result = await db.execute(text("SELECT COUNT(*) FROM papers"))
    return result.scalar() or 0
