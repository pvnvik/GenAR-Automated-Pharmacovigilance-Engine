"""Human review states, flags, and review audit records."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReviewStatus(str, Enum):
    DRAFT = "DRAFT"
    QA_CHECKED = "QA_CHECKED"
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FINAL = "FINAL"


class ReviewFlag(BaseModel):
    """Specific finding requiring human review attention."""
    flag_id: str
    flag_type: str
    severity: str
    description: str
    section_id: str
    evidence_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReviewRecord(BaseModel):
    """Record of human review decision and audit trail for a section or report."""
    review_id: str
    section_id: str
    status: ReviewStatus
    reviewer_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    comments: List[str] = Field(default_factory=list)
    flags: List[ReviewFlag] = Field(default_factory=list)
    approved_content: Optional[str] = None
    audit_metadata: Dict[str, Any] = Field(default_factory=dict)
