"""Recommendation engine using pgvector nearest neighbor search."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.serializers import paper_row_to_dict


async def similar_papers(db: AsyncSession, paper_id: str, limit: int = 20) -> list[dict]:
    """Find papers similar to the given paper using vector cosine similarity."""
    sql = text("""
        SELECT p2.id, p2.title, p2.summary, p2.authors, p2.categories,
               p2.pdf_url, p2.published_at, p2.updated_at,
               1 - (p1.embedding <=> p2.embedding) AS similarity
        FROM papers p1, papers p2
        WHERE p1.id = :paper_id
          AND p2.id != :paper_id
          AND p2.embedding IS NOT NULL
          AND p1.embedding IS NOT NULL
        ORDER BY p1.embedding <=> p2.embedding
        LIMIT :limit
    """)
    result = await db.execute(sql, {"paper_id": paper_id, "limit": limit})
    return [paper_row_to_dict(row) for row in result.fetchall()]


async def recommend_for_tag(
    db: AsyncSession,
    tag_id: int,
    limit: int = 25,
    days: int | None = None,
    exclude_tagged: bool = True,
) -> list[dict]:
    """Recommend papers similar to the centroid of all papers in a tag."""
    centroid_sql = text("""
        SELECT AVG(p.embedding)::text AS centroid
        FROM paper_tags pt
        JOIN papers p ON p.id = pt.paper_id
        WHERE pt.tag_id = :tag_id AND p.embedding IS NOT NULL
    """)
    result = await db.execute(centroid_sql, {"tag_id": tag_id})
    row = result.fetchone()
    if row is None or row.centroid is None:
        return []

    centroid_str = row.centroid

    time_filter = ""
    params: dict = {"centroid": centroid_str, "limit": limit, "tag_id": tag_id}

    if days:
        time_filter = "AND p.published_at > NOW() - make_interval(days => :days)"
        params["days"] = days

    exclude_filter = ""
    if exclude_tagged:
        exclude_filter = "AND p.id NOT IN (SELECT paper_id FROM paper_tags WHERE tag_id = :tag_id)"

    sql = text(f"""
        SELECT p.id, p.title, p.summary, p.authors, p.categories,
               p.pdf_url, p.published_at, p.updated_at,
               1 - (p.embedding <=> CAST(:centroid AS vector)) AS similarity
        FROM papers p
        WHERE p.embedding IS NOT NULL
          {time_filter}
          {exclude_filter}
        ORDER BY p.embedding <=> CAST(:centroid AS vector)
        LIMIT :limit
    """)
    result = await db.execute(sql, params)
    return [paper_row_to_dict(row) for row in result.fetchall()]


async def recommend_for_user(
    db: AsyncSession,
    user_id: str,
    limit: int = 25,
    days: int | None = 7,
) -> list[dict]:
    """Personalized feed based on the centroid of all user-tagged papers."""
    centroid_sql = text("""
        SELECT AVG(p.embedding)::text AS centroid
        FROM paper_tags pt
        JOIN tags t ON t.id = pt.tag_id
        JOIN papers p ON p.id = pt.paper_id
        WHERE t.user_id = CAST(:user_id AS uuid) AND p.embedding IS NOT NULL
    """)
    result = await db.execute(centroid_sql, {"user_id": user_id})
    row = result.fetchone()
    if row is None or row.centroid is None:
        return []

    centroid_str = row.centroid
    params: dict = {"centroid": centroid_str, "limit": limit, "user_id": user_id}

    time_filter = ""
    if days:
        time_filter = "AND p.published_at > NOW() - make_interval(days => :days)"
        params["days"] = days

    sql = text(f"""
        SELECT p.id, p.title, p.summary, p.authors, p.categories,
               p.pdf_url, p.published_at, p.updated_at,
               1 - (p.embedding <=> CAST(:centroid AS vector)) AS similarity
        FROM papers p
        WHERE p.embedding IS NOT NULL
          AND p.id NOT IN (
              SELECT pt.paper_id FROM paper_tags pt
              JOIN tags t ON t.id = pt.tag_id
              WHERE t.user_id = CAST(:user_id AS uuid)
          )
          {time_filter}
        ORDER BY p.embedding <=> CAST(:centroid AS vector)
        LIMIT :limit
    """)
    result = await db.execute(sql, params)
    return [paper_row_to_dict(row) for row in result.fetchall()]


async def papers_by_authors(
    db: AsyncSession,
    author_names: list[str],
    exclude_paper_id: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Find papers by matching author names in the JSONB authors column."""
    if not author_names:
        return []

    names_to_search = author_names[:3]
    conditions = " OR ".join(
        f"EXISTS (SELECT 1 FROM jsonb_array_elements(p.authors) AS a WHERE a->>'name' = :name_{i})"
        for i in range(len(names_to_search))
    )
    params: dict = {f"name_{i}": name for i, name in enumerate(names_to_search)}
    params["limit"] = limit

    exclude = ""
    if exclude_paper_id:
        exclude = "AND p.id != :exclude_id"
        params["exclude_id"] = exclude_paper_id

    sql = text(f"""
        SELECT p.id, p.title, p.summary, p.authors, p.categories,
               p.pdf_url, p.published_at, p.updated_at
        FROM papers p
        WHERE ({conditions})
          {exclude}
        ORDER BY p.published_at DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, params)
    return [paper_row_to_dict(row) for row in result.fetchall()]
