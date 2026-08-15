"""Unit and integration tests for Phase 8 (Review & Traceability) and Phase 9 (Export & Packaging)."""

import json
from pathlib import Path
import pytest
from click.testing import CliRunner

from genar.analyses.registry import AnalysisRegistry
from genar.cli import cli
from genar.config import load_dataset_config, load_report_config
from genar.evidence import EvidenceStore, build_all_packets
from genar.export import (
    export_audit_manifest,
    export_html_report,
    export_markdown_report,
)
from genar.generation.dispatcher import SectionGenerator
from genar.ingest.canonicalizer import run_canonicalization
from genar.ingest.loader import load_raw_dataframe
from genar.models.report import ReportDocument, ReportMetadata
from genar.models.review import ReviewStatus
from genar.review.traceability import EvidenceFactChecker
from genar.review.workflow import ReviewWorkflow


@pytest.fixture(scope="module")
def pipeline_context(sample_dataset_config_path: Path, sample_report_config_path: Path):
    """Fixture providing populated store, generated drafts, and report config."""
    dataset_cfg = load_dataset_config(sample_dataset_config_path)
    report_cfg = load_report_config(sample_report_config_path)

    raw_df = load_raw_dataframe(dataset_cfg.raw_data_path)
    cases_df, reactions_df, _ = run_canonicalization(raw_df, dataset_cfg)

    results = AnalysisRegistry.run_all(cases_df, reactions_df, dataset_cfg)
    store = EvidenceStore()
    store.add_many(results)

    packets = build_all_packets(report_cfg, store, dataset_cfg)
    generator = SectionGenerator()
    drafts = generator.generate_all(report_cfg, packets)

    return report_cfg, dataset_cfg, store, packets, drafts


def test_review_workflow_approval_states(pipeline_context):
    """Verify ReviewWorkflow approval tracking, comments, and status transitions."""
    _, _, _, _, drafts = pipeline_context
    workflow = ReviewWorkflow(drafts)

    assert not workflow.is_fully_approved()
    records = workflow.get_review_records()
    assert all(r.status == ReviewStatus.PENDING_REVIEW for r in records)

    # Approve one section
    rec1 = workflow.approve_section("executive_summary", reviewer_name="Dr. Smith", comments="Verified against source")
    assert rec1.status == ReviewStatus.APPROVED
    assert rec1.reviewer_name == "Dr. Smith"
    assert "Verified against source" in rec1.comments

    # Reject one section
    rec2 = workflow.reject_section("demographics", reviewer_name="Dr. Jones", reason="Check age bucket formatting")
    assert rec2.status == ReviewStatus.REJECTED
    assert not workflow.is_fully_approved()

    # Approve all
    workflow.approve_all(reviewer_name="Chief Safety Officer")
    assert workflow.is_fully_approved()


def test_evidence_fact_checker_verification(pipeline_context):
    """Verify EvidenceFactChecker validates numbers and constructs claim citations."""
    _, _, _, packets, drafts = pipeline_context
    exec_draft = next(d for d in drafts if d.section_id == "executive_summary")
    exec_pkt = packets["executive_summary"]

    report = EvidenceFactChecker.verify_section(exec_draft, exec_pkt)
    assert report.is_fully_grounded
    assert report.total_claims_checked > 0
    assert report.verified_claims_count > 0

    # Verify citation fields
    cit = next(c for c in report.citations if c.metric_value is not None)
    assert cit.section_id == "executive_summary"
    assert cit.analysis_id is not None
    assert cit.method_name is not None


def test_export_markdown_report(pipeline_context, tmp_path: Path):
    """Verify Markdown report export formatting and review sign-off section."""
    report_cfg, dataset_cfg, _, _, drafts = pipeline_context
    workflow = ReviewWorkflow(drafts)
    workflow.approve_all(reviewer_name="Safety Lead")

    meta = ReportMetadata(
        report_id="PADER-BISOPROLOL-TEST",
        report_type="PADER",
        product_name="Bisoprolol",
        manufacturer="Aurobindo Pharma",
        reporting_period_start=dataset_cfg.reporting_period_start,
        reporting_period_end=dataset_cfg.reporting_period_end,
        run_id="test-run-1",
        app_version="0.1.0",
        config_file="configs/pader.yaml",
        dataset_file="configs/dataset/bisoprolol.yaml",
        is_fully_approved=True,
    )
    doc = ReportDocument(
        metadata=meta,
        sections=workflow.get_drafts(),
        review_records=workflow.get_review_records(),
    )

    out_file = tmp_path / "pader_test.md"
    exported_path = export_markdown_report(doc, out_file)

    assert exported_path.exists()
    content = exported_path.read_text(encoding="utf-8")
    assert "# PADER: Periodic Adverse Drug Experience Report" in content
    assert "**Approval Status:** [APPROVED]" in content
    assert "## Review & Verification Sign-Off" in content
    assert "Safety Lead" in content


def test_export_html_report(pipeline_context, tmp_path: Path):
    """Verify standalone HTML report generation with styled KPI tiles and tables."""
    report_cfg, dataset_cfg, _, _, drafts = pipeline_context
    workflow = ReviewWorkflow(drafts)
    workflow.approve_all()

    meta = ReportMetadata(
        report_id="PADER-HTML-TEST",
        report_type="PADER",
        product_name="Bisoprolol",
        manufacturer="Aurobindo Pharma",
        reporting_period_start=dataset_cfg.reporting_period_start,
        reporting_period_end=dataset_cfg.reporting_period_end,
        run_id="test-run-html",
        app_version="0.1.0",
        config_file="configs/pader.yaml",
        dataset_file="configs/dataset/bisoprolol.yaml",
        is_fully_approved=True,
    )
    doc = ReportDocument(
        metadata=meta,
        sections=workflow.get_drafts(),
        review_records=workflow.get_review_records(),
    )

    out_file = tmp_path / "pader_test.html"
    exported_path = export_html_report(doc, out_file)

    assert exported_path.exists()
    content = exported_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "Bisoprolol - PADER Safety Report" in content
    assert "1,024" in content
    assert "1,023 (99.9%)" in content
    assert "styled-table" in content
    assert "badge-approved" in content


def test_export_audit_manifest(pipeline_context, tmp_path: Path):
    """Verify machine-readable JSON provenance manifest structure and citations."""
    report_cfg, dataset_cfg, store, packets, drafts = pipeline_context
    workflow = ReviewWorkflow(drafts)
    workflow.approve_all()

    all_citations = []
    for d in drafts:
        report = EvidenceFactChecker.verify_section(d, packets[d.section_id])
        all_citations.extend(report.citations)

    meta = ReportMetadata(
        report_id="PADER-MANIFEST-TEST",
        report_type="PADER",
        product_name="Bisoprolol",
        manufacturer="Aurobindo Pharma",
        reporting_period_start=dataset_cfg.reporting_period_start,
        reporting_period_end=dataset_cfg.reporting_period_end,
        run_id="test-run-man",
        app_version="0.1.0",
        config_file="configs/pader.yaml",
        dataset_file="configs/dataset/bisoprolol.yaml",
        is_fully_approved=True,
    )
    doc = ReportDocument(
        metadata=meta,
        sections=workflow.get_drafts(),
        review_records=workflow.get_review_records(),
    )

    out_file = tmp_path / "manifest_test.json"
    manifest_path = export_audit_manifest(doc, store, all_citations, out_file)

    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["manifest_version"] == "1.0"
    assert data["dataset"]["canonical_cases"] == 1024
    assert len(data["deterministic_analyses"]) >= 7
    assert data["deterministic_analyses"]["total_case_volume"]["contributing_cases_count"] == 1024
    assert data["fully_approved"] is True
    assert data["claim_citations_count"] > 0


def test_cli_run_pipeline_end_to_end(tmp_path: Path):
    """Verify full end-to-end CLI pipeline runs cleanly and generates all artifacts."""
    runner = CliRunner()
    out_dir = tmp_path / "pipeline_output"
    result = runner.invoke(cli, ["run-pipeline", "-o", str(out_dir)])

    assert result.exit_code == 0
    assert "Report Pipeline Completed Successfully!" in result.output
    assert (out_dir / "pader_report.md").exists()
    assert (out_dir / "pader_report.html").exists()
    assert (out_dir / "provenance_manifest.json").exists()

    # Validate generated JSON manifest
    manifest_data = json.loads((out_dir / "provenance_manifest.json").read_text(encoding="utf-8"))
    assert manifest_data["fully_approved"] is True
    assert len(manifest_data["section_reviews"]) == 8
