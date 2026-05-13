from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.db.base import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(BigInteger, unique=True, nullable=False, index=True)
    login = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    avatar_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=_now, nullable=False)
    last_login = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    jobs = relationship("AnalysisJob", back_populates="user", lazy="selectin")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id = Column(String(36), primary_key=True)   # UUID
    repo = Column(String(255), nullable=False, index=True)
    status = Column(
        Enum("pending", "running", "completed", "error", name="job_status"),
        default="pending",
        nullable=False,
    )
    progress = Column(Integer, default=0, nullable=False)
    total = Column(Integer, default=0, nullable=False)
    processed = Column(Integer, default=0, nullable=False)
    message = Column(String(512), default="", nullable=False)
    started_at = Column(DateTime, default=_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user = relationship("User", back_populates="jobs")


class PullRequest(Base):
    __tablename__ = "pull_requests"
    __table_args__ = (
        UniqueConstraint("repo", "number", name="uq_pr_repo_number"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(BigInteger, nullable=True)
    number = Column(Integer, nullable=False, index=True)
    repo = Column(String(255), nullable=False, index=True)

    title = Column(String(512), nullable=False, default="")
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=False, default="")
    author_avatar = Column(String(512), nullable=True)
    url = Column(String(512), nullable=True)

    # AI analysis results
    topics = Column(JSON, default=list)          # ["vectordb", "engine", ...]
    score = Column(Integer, default=0)           # 0–100
    recommendation = Column(
        Enum("merge", "keep", "discard", "combine", name="pr_recommendation"),
        default="keep",
    )
    summary = Column(Text, nullable=True)
    reasoning = Column(Text, nullable=True)
    similar_prs = Column(JSON, default=list)     # [42, 17, ...]
    files_changed = Column(JSON, default=list)   # ["src/foo.py", ...]
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)

    review_status = Column(
        Enum("changes_requested", "approved", "commented", name="pr_review_status"),
        nullable=True,
    )
    reviewers = Column(JSON, default=list)  # [{"login": "user", "state": "APPROVED"}, ...]
    status = Column(
        Enum("analyzed", "pending", "error", name="pr_status"),
        default="pending",
    )
    github_created_at = Column(String(32), nullable=True)
    analyzed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String(36), primary_key=True)
    repo = Column(String(255), nullable=False, index=True)
    status = Column(
        Enum("pending", "running", "completed", "error", name="ingestion_status"),
        default="pending",
        nullable=False,
    )
    progress = Column(Integer, default=0, nullable=False)
    total = Column(Integer, default=0, nullable=False)
    processed = Column(Integer, default=0, nullable=False)
    message = Column(String(512), default="", nullable=False)
    started_at = Column(DateTime, default=_now, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user = relationship("User", lazy="selectin")


class ReviewAction(Base):
    __tablename__ = "review_actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pr_number = Column(Integer, nullable=False, index=True)
    repo = Column(String(255), nullable=False, index=True)
    event = Column(
        Enum("APPROVE", "REQUEST_CHANGES", "COMMENT", name="review_event"),
        nullable=False,
    )
    body = Column(Text, nullable=False)
    viability_score = Column(Integer, default=0)
    github_review_id = Column(BigInteger, nullable=True)
    submitted_by = Column(String(255), nullable=True)
    submitted_at = Column(DateTime, default=_now, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)
