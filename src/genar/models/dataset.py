"""Domain models for dataset records, canonical views, and metadata."""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RawCaseRecord(BaseModel):
    """Represents a single raw row ingested from the safety dataset."""
    raw_row_id: int
    safety_report_id: str
    received_date: Optional[date] = None
    receipt_date: Optional[date] = None
    serious: Optional[int] = None
    seriousness_death: Optional[int] = None
    seriousness_lifethreatening: Optional[int] = None
    seriousness_hospitalization: Optional[int] = None
    seriousness_disabling: Optional[int] = None
    seriousness_congenitalanomali: Optional[int] = None
    seriousness_other: Optional[int] = None
    patient_sex: Optional[str] = None
    patient_age: Optional[float] = None
    patient_age_group: Optional[str] = None
    primary_source_country: Optional[str] = None
    reaction_meddra_pt: Optional[str] = None
    reaction_outcome: Optional[str] = None
    drug_characterization: Optional[str] = None
    medicinal_product: Optional[str] = None
    raw_fields: Dict[str, Any] = Field(default_factory=dict)


class CanonicalCase(BaseModel):
    """Canonical case-level representation (one record per unique case)."""
    safety_report_id: str
    received_date: Optional[date] = None
    receipt_date: Optional[date] = None
    is_serious: bool = False
    is_death: bool = False
    is_life_threatening: bool = False
    is_hospitalization: bool = False
    is_disabling: bool = False
    is_congenital_anomaly: bool = False
    is_other_medically_important: bool = False
    is_15_day_alert: bool = False
    patient_sex: str = "UNKNOWN"
    patient_age: Optional[float] = None
    patient_age_group: str = "UNKNOWN"
    primary_source_country: str = "UNKNOWN"
    primary_medicinal_product: Optional[str] = None
    reactions_count: int = 0
    source_row_indices: List[int] = Field(default_factory=list)
    version_count: int = 1
    has_dq_warnings: bool = False


class ReactionRecord(BaseModel):
    """Exploded reaction-level record (one record per reaction occurrence)."""
    reaction_id: str
    safety_report_id: str
    reaction_pt: str
    reaction_outcome: str = "UNKNOWN"
    is_positionally_aligned: bool = True
    is_case_serious: bool = False
    received_date: Optional[date] = None
    patient_sex: str = "UNKNOWN"
    patient_age_group: str = "UNKNOWN"
    country: str = "UNKNOWN"
    source_row_index: int


class DatasetMetadata(BaseModel):
    """Dataset level summary and ingestion metadata."""
    dataset_name: str
    file_path: str
    total_raw_rows: int
    total_canonical_cases: int
    total_reactions: int
    reporting_period_start: Optional[date] = None
    reporting_period_end: Optional[date] = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checksum: Optional[str] = None
