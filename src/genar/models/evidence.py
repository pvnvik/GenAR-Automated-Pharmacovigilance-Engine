"""Evidence models and section-specific evidence packets."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EvidenceProvenance(BaseModel):
    """Traceability metadata linking a fact back to deterministic analysis."""
    analysis_id: str
    version: str
    category: str
    calculated_at: datetime
    method_name: str
    contributing_cases_count: Optional[int] = None
    sample_case_ids: Optional[List[str]] = None


class EvidenceItem(BaseModel):
    """A discrete, verified factual claim or statistic."""
    evidence_id: str
    title: str
    metric_key: str
    value: Any
    formatted_value: str
    provenance: EvidenceProvenance
    description: Optional[str] = None
    table_representation: Optional[List[Dict[str, Any]]] = None


class EvidencePacket(BaseModel):
    """Section-scoped evidence packet delivered to section generators."""
    section_id: str
    section_title: str
    dataset_name: str
    reporting_period: str
    items: Dict[str, EvidenceItem] = Field(default_factory=dict)
    summary_metrics: Dict[str, Any] = Field(default_factory=dict)
    table_data: Optional[List[Dict[str, Any]]] = None
    non_invention_notes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
