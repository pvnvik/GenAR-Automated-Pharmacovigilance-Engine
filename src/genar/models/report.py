"""Final assembled report models, metadata, and export artifacts."""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from genar.models.quality import DataQualityReport
from genar.models.review import ReviewRecord
from genar.models.section import SectionDraft


class ReportMetadata(BaseModel):
    """Metadata stamped onto every generated report and audit trail."""
    report_id: str
    report_type: str = "PADER"
    product_name: str
    manufacturer: str
    reporting_period_start: date
    reporting_period_end: date
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    run_id: str
    app_version: str
    config_file: str
    dataset_file: str
    is_fully_approved: bool = False


class ReportDocument(BaseModel):
    """Canonical assembled report container containing all sections and provenance."""
    metadata: ReportMetadata
    sections: List[SectionDraft] = Field(default_factory=list)
    quality_report: Optional[DataQualityReport] = None
    review_records: List[ReviewRecord] = Field(default_factory=list)
    full_markdown: str = ""
    render_formats: List[str] = Field(default_factory=lambda: ["markdown"])
    custom_metadata: Dict[str, Any] = Field(default_factory=dict)
