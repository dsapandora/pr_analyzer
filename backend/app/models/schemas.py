from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class Recommendation(str, Enum):
    merge = "merge"
    keep = "keep"
    discard = "discard"
    combine = "combine"


class PRStatus(str, Enum):
    analyzed = "analyzed"
    pending = "pending"
    error = "error"


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    error = "error"


class PRSchema(BaseModel):
    id: int
    number: int
    title: str
    description: str = ""
    author: str
    author_avatar: str = Field("", alias="authorAvatar")
    url: str
    topics: List[str] = []
    score: int = 0
    recommendation: Recommendation = Recommendation.keep
    similar_prs: List[int] = Field([], alias="similarPRs")
    files_changed: List[str] = Field([], alias="filesChanged")
    additions: int = 0
    deletions: int = 0
    status: PRStatus = PRStatus.pending
    created_at: str = Field("", alias="createdAt")
    summary: Optional[str] = None
    reasoning: Optional[str] = None
    repo: Optional[str] = None

    class Config:
        populate_by_name = True


class PRAnalysis(BaseModel):
    topics: List[str]
    summary: str
    recommendation: Recommendation
    score: int = Field(ge=0, le=100)
    reasoning: str
    embedding: Optional[List[float]] = None


class AnalyzeRequest(BaseModel):
    repo: str = Field(..., description="Full repository name: owner/repo")


class AnalyzeJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = 0
    total: int = 0
    processed: int = 0
    message: str = ""
    started_at: str
    completed_at: Optional[str] = None


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    pr_number: int
    repo: str
    message: str
    history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    message: str
    pr_number: int


class RepositorySchema(BaseModel):
    id: int
    name: str
    full_name: str
    description: Optional[str] = None
    private: bool = False
    language: Optional[str] = None
    stargazers_count: int = 0
    open_prs_count: int = 0


class StatsResponse(BaseModel):
    total: int
    analyzed: int
    duplicates: int
    topics: int
    recommended: Dict[str, int]


# ---------------------------------------------------------------------------
# Criteria ingestion
# ---------------------------------------------------------------------------

class IngestCriteriaRequest(BaseModel):
    repo: str = Field(default="rocketride-io/rocketride-server")
    authors: Optional[List[str]] = None


# ---------------------------------------------------------------------------
# Review generation & submission
# ---------------------------------------------------------------------------

class CommentAnalysisItem(BaseModel):
    author: str
    body: str
    status: str  # applied, not_applied, partial
    explanation: str

class ViabilityAssessment(BaseModel):
    viability_score: int = Field(ge=0, le=100)
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []
    overall_assessment: str = ""

class ReviewGenerateRequest(BaseModel):
    pr_number: int
    repo: str

class TicketEvaluation(BaseModel):
    ticket_makes_sense: bool = True
    implementation_matches_ticket: bool = True
    is_redundant: bool = False
    is_counterproductive: bool = False
    risk_level: str = "low"
    risk_reasons: List[str] = []
    ticket_assessment: str = ""
    implementation_assessment: str = ""
    needs_human_review: bool = False
    human_review_reason: str = ""

class ReviewGenerateResponse(BaseModel):
    body: str
    event: str
    viability: ViabilityAssessment
    comment_analysis: List[CommentAnalysisItem] = []
    ticket_eval: Optional[TicketEvaluation] = None
    risk_level: str = "low"
    needs_human_review: bool = False
    human_review_reason: str = ""

class ReviewSubmitRequest(BaseModel):
    pr_number: int
    repo: str
    body: str
    event: str = Field(..., pattern="^(APPROVE|REQUEST_CHANGES|COMMENT)$")

class ReviewSubmitResponse(BaseModel):
    github_review_id: int
    pr_number: int
    event: str
    submitted_at: str
    fallback: str = ""

class RelatedPRInfo(BaseModel):
    number: int
    title: str
    score: int
    recommendation: str
    summary: str = ""
    is_primary: bool = False
