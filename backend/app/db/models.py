import uuid
from datetime import datetime

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
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(320), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    is_email_verified = Column(Boolean, nullable=False, server_default="false")
    email_verification_token = Column(String(128), nullable=True)
    password_reset_token = Column(String(128), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

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


class Collection(Base):
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True, default="")
    is_public = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="collections")
    papers = relationship("CollectionPaper", back_populates="collection", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_collection_user_name"),
    )


class CollectionPaper(Base):
    __tablename__ = "collection_papers"

    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True)
    paper_id = Column(String(20), ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    note = Column(Text, nullable=True, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    collection = relationship("Collection", back_populates="papers")
    paper = relationship("Paper", back_populates="collection_entries")


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
