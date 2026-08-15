"""Data quality issues, severity definitions, and quality reporting models."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DQSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class DQIssueType(str, Enum):
    DUPLICATE_CASE_ID = "DUPLICATE_CASE_ID"
    UPDATED_CASE_ROW = "UPDATED_CASE_ROW"
    LIST_LENGTH_MISMATCH = "LIST_LENGTH_MISMATCH"
    INVALID_DATE_FORMAT = "INVALID_DATE_FORMAT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_VALUE = "INVALID_VALUE"
    AGE_OUT_OF_RANGE = "AGE_OUT_OF_RANGE"
    UNPARSED_FIELD = "UNPARSED_FIELD"


class DQActionTaken(str, Enum):
    FLAGGED = "FLAGGED"
    DEDUPLICATED_LATEST = "DEDUPLICATED_LATEST"
    POSITIONALLY_REJECTED = "POSITIONALLY_REJECTED"
    KEPT_AS_IS = "KEPT_AS_IS"
    EXCLUDED_FROM_REACTION_ANALYSIS = "EXCLUDED_FROM_REACTION_ANALYSIS"


class DQIssue(BaseModel):
    """Represents a discrete data quality finding or anomaly."""
    issue_type: DQIssueType
    severity: DQSeverity
    safety_report_id: Optional[str] = None
    row_index: Optional[int] = None
    field_name: Optional[str] = None
    raw_value: Optional[Any] = None
    message: str
    action_taken: DQActionTaken = DQActionTaken.FLAGGED
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DataQualityReport(BaseModel):
    """Aggregated data quality report to be surfaced to human reviewers."""
    total_raw_rows: int
    total_unique_case_ids: int
    duplicate_rows_detected: int = 0
    list_mismatches_detected: int = 0
    critical_issues_count: int = 0
    warning_issues_count: int = 0
    info_issues_count: int = 0
    issues: List[DQIssue] = Field(default_factory=list)
    summary_by_type: Dict[str, int] = Field(default_factory=dict)
