"""Analysis result models with full provenance tracking."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalysisCategory(str, Enum):
    VOLUME = "volume"
    SERIOUSNESS = "seriousness"
    DEMOGRAPHICS = "demographics"
    REACTIONS = "reactions"
    OUTCOMES = "outcomes"
    ALERTS = "alerts"
    TRENDS = "trends"
    CUSTOM = "custom"


class AnalysisResult(BaseModel):
    """Encapsulates the exact result of a registered deterministic calculation."""
    analysis_id: str
    version: str = "1.0"
    name: str
    description: str
    category: AnalysisCategory
    dataset_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    contributing_case_ids: Optional[List[str]] = None
    execution_time_ms: Optional[float] = None
    calculated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    method_name: str
    config_hash: Optional[str] = None
