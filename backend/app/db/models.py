import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Paper(Base):
    __tablename__ = "papers"

    id = Column(String(20), primary_key=True, comment="arXiv ID e.g. 2301.12345")
    title = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    authors = Column(JSONB, nullable=False, default=list)
    categories = Column(ARRAY(String), nullable=False, default=list)
    pdf_url = Column(String(512), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    embedding = Column(Vector(384), nullable=True)
    tsv = Column(TSVECTOR, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tags = relationship("PaperTag", back_populates="paper", cascade="all, delete-orphan")
    collection_entries = relationship("CollectionPaper", back_populates="paper", cascade="all, delete-orphan")
    saved_by = relationship("SavedPaper", back_populates="paper", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_papers_published_at", "published_at"),
        Index("ix_papers_tsv", "tsv", postgresql_using="gin"),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(320), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    is_email_verified = Column(Boolean, nullable=False, server_default="false")
    email_verification_token = Column(String(128), nullable=True)
    password_reset_token = Column(String(128), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    digest_enabled = Column(Boolean, nullable=False, server_default="false")
    digest_frequency = Column(String(20), nullable=False, server_default="daily")

    tags = relationship("Tag", back_populates="user", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")
    saved_papers = relationship("SavedPaper", back_populates="user", cascade="all, delete-orphan")
    webhook_configs = relationship("WebhookConfig", back_populates="user", cascade="all, delete-orphan")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="tags")
    paper_tags = relationship("PaperTag", back_populates="tag", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_tag_user_name"),
    )


class PaperTag(Base):
    __tablename__ = "paper_tags"

    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
    paper_id = Column(String(20), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tag = relationship("Tag", back_populates="paper_tags")
    paper = relationship("Paper", back_populates="tags")


def _generate_share_slug() -> str:
    return uuid.uuid4().hex[:10]


class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True, default="")
    is_public = Column(Boolean, nullable=False, default=False)
    share_slug = Column(String(60), unique=True, nullable=True, default=_generate_share_slug)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="collections")
    papers = relationship("CollectionPaper", back_populates="collection", cascade="all, delete-orphan")
    views = relationship("CollectionView", back_populates="collection", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_collection_user_name"),
        Index("ix_collections_is_public", "is_public"),
    )


class CollectionPaper(Base):
    __tablename__ = "collection_papers"

    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True)
    paper_id = Column(String(20), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    note = Column(Text, nullable=True, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    collection = relationship("Collection", back_populates="papers")
    paper = relationship("Paper", back_populates="collection_entries")


class CollectionView(Base):
    __tablename__ = "collection_views"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    session_hash = Column(String(64), nullable=False)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    collection = relationship("Collection", back_populates="views")

    __table_args__ = (
        Index("ix_collection_views_coll_viewed", "collection_id", "viewed_at"),
    )


class SavedPaper(Base):
    __tablename__ = "saved_papers"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    paper_id = Column(String(20), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="saved_papers")
    paper = relationship("Paper", back_populates="saved_by")


class WebhookConfig(Base):
    __tablename__ = "webhook_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(20), nullable=False, comment="slack or discord")
    webhook_url = Column(String(512), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="webhook_configs")
    tag = relationship("Tag")


class CitationCache(Base):
    __tablename__ = "citation_cache"

    paper_id = Column(String(20), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    status = Column(String(20), nullable=False, server_default="pending", comment="pending|fetched|not_found|error")
    data = Column(JSONB, nullable=False, default=dict)
    fetched_at = Column(DateTime(timezone=True), nullable=True)
    retry_after = Column(DateTime(timezone=True), nullable=True)
    error_count = Column(Integer, nullable=False, server_default="0")


class PaperView(Base):
    __tablename__ = "paper_views"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(String(20), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    session_hash = Column(String(64), nullable=False)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_paper_views_paper_viewed", "paper_id", "viewed_at"),
    )


class PaperFulltext(Base):
    __tablename__ = "paper_fulltext"

    paper_id = Column(String(20), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    source = Column(String(20), nullable=False, comment="latex | ar5iv_html | pdf")
    content = Column(Text, nullable=True)
    sections = Column(JSONB, nullable=True)
    char_count = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, server_default="pending", comment="pending|extracted|failed")
    extracted_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)


class PaperChunk(Base):
    __tablename__ = "paper_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(String(20), ForeignKey("papers.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    section_title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    embedding = Column(Vector(384), nullable=True)

    __table_args__ = (
        Index("ix_paper_chunks_paper_id", "paper_id"),
        Index("ix_paper_chunks_paper_chunk", "paper_id", "chunk_index", unique=True),
    )


class BackfillState(Base):
    __tablename__ = "backfill_state"

    id = Column(String(50), primary_key=True)
    cursor_date = Column(DateTime(timezone=True), nullable=True)
    is_complete = Column(Boolean, nullable=False, server_default="false")
    papers_processed = Column(Integer, nullable=False, server_default="0")
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    extra_data = Column(JSONB, nullable=False, server_default="{}")
