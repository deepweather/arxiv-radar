"""Embedding-based classifier recommender using logistic regression."""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.serializers import paper_row_to_dict


async def _get_user_tagged_papers(db: AsyncSession, user_id: str) -> list[dict]:
    """Get all papers tagged by a user with their embeddings."""
    sql = text("""
        SELECT DISTINCT p.id, p.title, p.embedding
        FROM paper_tags pt
        JOIN tags t ON t.id = pt.tag_id
        JOIN papers p ON p.id = pt.paper_id
        WHERE t.user_id = CAST(:user_id AS uuid)
          AND p.embedding IS NOT NULL
    """)
    result = await db.execute(sql, {"user_id": user_id})
    rows = result.fetchall()
    return [{"id": row.id, "title": row.title, "embedding": np.array(row.embedding)} for row in rows]


async def _get_negative_samples(
    db: AsyncSession, 
    user_id: str, 
    exclude_ids: list[str],
    limit: int = 500,
) -> list[dict]:
    """Get random negative samples (papers not tagged by user)."""
    params = {"user_id": user_id, "limit": limit}
    
    exclude_filter = ""
    if exclude_ids:
        exclude_filter = "AND p.id != ALL(:exclude_ids)"
        params["exclude_ids"] = exclude_ids
    
    sql = text(f"""
        SELECT p.id, p.embedding
        FROM papers p
        WHERE p.embedding IS NOT NULL
          AND p.id NOT IN (
              SELECT pt.paper_id FROM paper_tags pt
              JOIN tags t ON t.id = pt.tag_id
              WHERE t.user_id = CAST(:user_id AS uuid)
          )
          {exclude_filter}
        ORDER BY RANDOM()
        LIMIT :limit
    """)
    result = await db.execute(sql, params)
    rows = result.fetchall()
    return [{"id": row.id, "embedding": np.array(row.embedding)} for row in rows]


def _train_classifier(
    positive_embeddings: np.ndarray,
    negative_embeddings: np.ndarray,
) -> LogisticRegression:
    """Train a logistic regression classifier."""
    X = np.vstack([positive_embeddings, negative_embeddings])
    y = np.concatenate([
        np.ones(len(positive_embeddings)),
        np.zeros(len(negative_embeddings)),
    ])
    
    clf = LogisticRegression(
        max_iter=200,
        class_weight="balanced",
        solver="lbfgs",
        random_state=42,
    )
    clf.fit(X, y)
    return clf


async def recommend_with_classifier(
    db: AsyncSession,
    user_id: str,
    limit: int = 25,
    days: int = 7,
) -> list[dict]:
    """
    Recommend papers using a logistic regression classifier trained on user's tagged papers.
    
    Returns papers sorted by classifier confidence score.
    Falls back to empty list if user has < 3 tagged papers.
    """
    positive_papers = await _get_user_tagged_papers(db, user_id)
    
    if len(positive_papers) < 3:
        return []
    
    positive_ids = [p["id"] for p in positive_papers]
    positive_embeddings = np.array([p["embedding"] for p in positive_papers])
    
    negative_samples = await _get_negative_samples(db, user_id, positive_ids, limit=500)
    if len(negative_samples) < 10:
        return []
    
    negative_embeddings = np.array([p["embedding"] for p in negative_samples])
    
    clf = _train_classifier(positive_embeddings, negative_embeddings)
    
    params: dict = {"user_id": user_id, "limit": limit * 5}
    time_filter = ""
    if days:
        time_filter = "AND p.published_at > NOW() - make_interval(days => :days)"
        params["days"] = days
    
    sql = text(f"""
        SELECT p.id, p.title, p.summary, p.authors, p.categories,
               p.pdf_url, p.published_at, p.updated_at, p.embedding
        FROM papers p
        WHERE p.embedding IS NOT NULL
          AND p.id NOT IN (
              SELECT pt.paper_id FROM paper_tags pt
              JOIN tags t ON t.id = pt.tag_id
              WHERE t.user_id = CAST(:user_id AS uuid)
          )
          {time_filter}
        ORDER BY p.published_at DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, params)
    candidate_rows = result.fetchall()
    
    if not candidate_rows:
        return []
    
    candidate_embeddings = np.array([np.array(row.embedding) for row in candidate_rows])
    scores = clf.predict_proba(candidate_embeddings)[:, 1]
    
    scored_papers = []
    for i, row in enumerate(candidate_rows):
        paper = paper_row_to_dict(row)
        paper["score"] = round(float(scores[i]), 4)
        scored_papers.append(paper)
    
    scored_papers.sort(key=lambda p: p["score"], reverse=True)
    
    return scored_papers[:limit]


async def recommend_with_classifier_and_explanation(
    db: AsyncSession,
    user_id: str,
    limit: int = 25,
    days: int = 7,
) -> list[dict]:
    """
    Recommend papers using classifier, with explanation showing most similar tagged papers.
    """
    positive_papers = await _get_user_tagged_papers(db, user_id)
    
    if len(positive_papers) < 3:
        return []
    
    positive_ids = [p["id"] for p in positive_papers]
    positive_embeddings = np.array([p["embedding"] for p in positive_papers])
    positive_titles = {p["id"]: p["title"] for p in positive_papers}
    
    negative_samples = await _get_negative_samples(db, user_id, positive_ids, limit=500)
    if len(negative_samples) < 10:
        return []
    
    negative_embeddings = np.array([p["embedding"] for p in negative_samples])
    
    clf = _train_classifier(positive_embeddings, negative_embeddings)
    
    params: dict = {"user_id": user_id, "limit": limit * 5}
    time_filter = ""
    if days:
        time_filter = "AND p.published_at > NOW() - make_interval(days => :days)"
        params["days"] = days
    
    sql = text(f"""
        SELECT p.id, p.title, p.summary, p.authors, p.categories,
               p.pdf_url, p.published_at, p.updated_at, p.embedding
        FROM papers p
        WHERE p.embedding IS NOT NULL
          AND p.id NOT IN (
              SELECT pt.paper_id FROM paper_tags pt
              JOIN tags t ON t.id = pt.tag_id
              WHERE t.user_id = CAST(:user_id AS uuid)
          )
          {time_filter}
        ORDER BY p.published_at DESC
        LIMIT :limit
    """)
    result = await db.execute(sql, params)
    candidate_rows = result.fetchall()
    
    if not candidate_rows:
        return []
    
    candidate_embeddings = np.array([np.array(row.embedding) for row in candidate_rows])
    scores = clf.predict_proba(candidate_embeddings)[:, 1]
    
    scored_papers = []
    for i, row in enumerate(candidate_rows):
        paper = paper_row_to_dict(row)
        paper["score"] = round(float(scores[i]), 4)
        
        candidate_emb = candidate_embeddings[i]
        similarities = np.dot(positive_embeddings, candidate_emb) / (
            np.linalg.norm(positive_embeddings, axis=1) * np.linalg.norm(candidate_emb) + 1e-8
        )
        
        top_indices = np.argsort(similarities)[-2:][::-1]
        paper["similar_to"] = [
            {
                "id": positive_ids[idx],
                "title": positive_titles[positive_ids[idx]],
                "similarity": round(float(similarities[idx]), 3),
            }
            for idx in top_indices
            if similarities[idx] > 0.3
        ]
        
        scored_papers.append(paper)
    
    scored_papers.sort(key=lambda p: p["score"], reverse=True)
    
    return scored_papers[:limit]
