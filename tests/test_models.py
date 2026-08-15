"""Tests for domain model validation and serialization."""

from datetime import date, datetime, timezone
from genar.models import (
    AnalysisCategory,
    AnalysisResult,
    CanonicalCase,
    DQActionTaken,
    DQIssue,
    DQIssueType,
    DQSeverity,
    DataQualityReport,
    DatasetMetadata,
    EvidenceItem,
    EvidencePacket,
    EvidenceProvenance,
    GenerationMode,
    RawCaseRecord,
    ReactionRecord,
    ReportDocument,
    ReportMetadata,
    ReviewFlag,
    ReviewRecord,
    ReviewStatus,
    SectionDraft,
)


def test_canonical_case_model():
    """Verify CanonicalCase model creation and defaults."""
    case = CanonicalCase(
        safety_report_id="123456",
        is_serious=True,
        is_hospitalization=True,
        patient_sex="FEMALE",
        patient_age=72.0,
        patient_age_group="Elderly (65+)",
        primary_source_country="US",
    )
    assert case.safety_report_id == "123456"
    assert case.is_serious is True
    assert case.is_death is False
    assert case.is_hospitalization is True
    assert case.patient_sex == "FEMALE"
    assert case.patient_age_group == "Elderly (65+)"


def test_dq_issue_and_report_models():
    """Verify Data Quality issue tracking models."""
    issue = DQIssue(
        issue_type=DQIssueType.DUPLICATE_CASE_ID,
        severity=DQSeverity.WARNING,
        safety_report_id="123456",
        row_index=12,
        field_name="safetyreportid",
        message="Duplicate safety report ID detected across multiple rows",
        action_taken=DQActionTaken.DEDUPLICATED_LATEST,
    )
    assert issue.severity == DQSeverity.WARNING
    assert issue.action_taken == DQActionTaken.DEDUPLICATED_LATEST

    report = DataQualityReport(
        total_raw_rows=1068,
        total_unique_case_ids=1024,
        duplicate_rows_detected=44,
        warning_issues_count=44,
        issues=[issue],
    )
    assert report.total_raw_rows == 1068
    assert report.total_unique_case_ids == 1024
    assert len(report.issues) == 1


def test_analysis_result_provenance():
    """Verify AnalysisResult captures calculation metadata."""
    result = AnalysisResult(
        analysis_id="volume_summary_v1",
        version="1.0",
        name="Case Volume Breakdown",
        description="Calculates total, serious, non-serious cases and 15-day alerts.",
        category=AnalysisCategory.VOLUME,
        dataset_id="bisoprolol_sample_2024",
        metrics={
            "total_cases": 1024,
            "serious_cases": 820,
            "non_serious_cases": 204,
            "fifteen_day_alerts": 12,
        },
        contributing_case_ids=["101", "102"],
        method_name="genar.analyses.volume.compute_volume_summary",
    )
    assert result.metrics["total_cases"] == 1024
    assert result.category == AnalysisCategory.VOLUME
    assert len(result.contributing_case_ids) == 2


def test_evidence_packet_structure():
    """Verify EvidencePacket and EvidenceItem models."""
    prov = EvidenceProvenance(
        analysis_id="volume_summary_v1",
        version="1.0",
        category="volume",
        calculated_at=datetime.now(timezone.utc),
        method_name="compute_volume_summary",
        contributing_cases_count=1024,
    )
    item = EvidenceItem(
        evidence_id="ev_total_volume",
        title="Total Case Volume",
        metric_key="total_cases",
        value=1024,
        formatted_value="1,024 cases",
        provenance=prov,
    )
    packet = EvidencePacket(
        section_id="executive_summary",
        section_title="1. Executive Summary & Overview",
        dataset_name="Bisoprolol 2024",
        reporting_period="2024-01-01 to 2024-12-31",
        items={"total_cases": item},
        summary_metrics={"total_cases": 1024},
    )
    assert packet.section_id == "executive_summary"
    assert packet.items["total_cases"].value == 1024


def test_report_document_and_review_models():
    """Verify SectionDraft, ReviewRecord, and ReportDocument composition."""
    draft = SectionDraft(
        section_id="executive_summary",
        title="Executive Summary",
        order=1,
        generation_mode=GenerationMode.TEMPLATE,
        markdown_content="## Executive Summary\nTotal cases: 1024",
        evidence_ids_used=["ev_total_volume"],
    )
    review = ReviewRecord(
        review_id="rev_001",
        section_id="executive_summary",
        status=ReviewStatus.APPROVED,
        reviewer_name="Regulatory Lead",
        comments=["Approved without modifications."],
    )
    meta = ReportMetadata(
        report_id="PADER-2024-001",
        report_type="PADER",
        product_name="Bisoprolol",
        manufacturer="Aurobindo",
        reporting_period_start=date(2024, 1, 1),
        reporting_period_end=date(2024, 12, 31),
        run_id="run_test_123",
        app_version="0.1.0",
        config_file="configs/pader.yaml",
        dataset_file="data/raw/Bisoprolol_icsr_sample_1068rows.xlsx",
        is_fully_approved=True,
    )
    doc = ReportDocument(
        metadata=meta,
        sections=[draft],
        review_records=[review],
        full_markdown="# PADER Report\n\n## Executive Summary\nTotal cases: 1024",
    )
    assert doc.metadata.product_name == "Bisoprolol"
    assert len(doc.sections) == 1
    assert doc.review_records[0].status == ReviewStatus.APPROVED
