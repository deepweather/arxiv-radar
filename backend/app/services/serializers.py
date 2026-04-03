"""Shared serialization helpers for paper data."""


def paper_row_to_dict(row) -> dict:
    """Convert a SQLAlchemy row from a papers query into an API-ready dict."""
    d = {
        "id": row.id,
        "title": row.title,
        "summary": row.summary,
        "authors": row.authors,
        "categories": row.categories,
        "pdf_url": row.pdf_url,
        "published_at": row.published_at.isoformat() if row.published_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
    if hasattr(row, "similarity") and row.similarity is not None:
        d["similarity"] = round(float(row.similarity), 4)
    if hasattr(row, "semantic_score") and row.semantic_score is not None:
        d["score"] = round(float(row.semantic_score), 4)
    return d
