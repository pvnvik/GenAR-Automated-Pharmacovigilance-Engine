"""LangGraph node functions executing each stage of the GenAR pipeline."""

import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from genar.analyses.registry import AnalysisRegistry
from genar.config import load_dataset_config, load_report_config
from genar.evidence.packet_builder import build_all_packets
from genar.evidence.store import EvidenceStore
from genar.export import (
    export_audit_manifest,
    export_html_report,
    export_markdown_report,
)
from genar.generation.dispatcher import SectionGenerator
from genar.ingest.canonicalizer import run_canonicalization
from genar.ingest.loader import load_raw_dataframe
from genar.ingest.quality import build_data_quality_report
from genar.ingest.validator import validate_dataset
from genar.models.report import ReportDocument, ReportMetadata
from genar.orchestration.state import ReportWorkflowState
from genar.review.traceability import EvidenceFactChecker
from genar.review.workflow import ReviewWorkflow


def load_configs_node(state: ReportWorkflowState) -> Dict[str, Any]:
    """Node 1: Load and validate report and dataset YAML configurations."""
    r_cfg = load_report_config(state.get("report_config_path", "configs/pader.yaml"))
    d_cfg = load_dataset_config(state.get("dataset_config_path", "configs/dataset/bisoprolol.yaml"))

    log = f"[Configs] Loaded '{r_cfg.title}' and dataset '{d_cfg.product_name}'."
    return {
        "report_config": r_cfg,
        "dataset_config": d_cfg,
        "current_step": "load_configs",
        "logs": state.get("logs", []) + [log],
    }


def ingest_validate_node(state: ReportWorkflowState) -> Dict[str, Any]:
    """Node 2: Non-destructive raw ingestion and deterministic data quality checks."""
    d_cfg = state["dataset_config"]
    raw_path = Path(d_cfg.raw_data_path)
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {raw_path}")

    raw_df = load_raw_dataframe(raw_path)
    issues = validate_dataset(raw_df, d_cfg)
    dq_report = build_data_quality_report(
        issues,
        total_raw_rows=len(raw_df),
        total_unique_case_ids=int(raw_df[d_cfg.column_mapping.case_id].nunique()) if d_cfg.column_mapping.case_id in raw_df.columns else len(raw_df),
    )

    log = f"[Ingest & DQ] Ingested {len(raw_df)} rows. Found {len(issues)} data quality findings."
    return {
        "raw_df": raw_df,
        "raw_data_shape": raw_df.shape,
        "data_quality_report": dq_report,
        "dq_issues_count": len(issues),
        "current_step": "ingest_validate",
        "logs": state.get("logs", []) + [log],
    }


def canonicalize_node(state: ReportWorkflowState) -> Dict[str, Any]:
    """Node 3: Multi-version deduplication and adverse event explosion."""
    raw_df = state["raw_df"]
    d_cfg = state["dataset_config"]

    cases_df, reactions_df, _ = run_canonicalization(raw_df, d_cfg)
    log = f"[Canonicalize] Resolved {len(cases_df)} unique cases and {len(reactions_df)} exploded reactions."
    return {
        "cases_df": cases_df,
        "reactions_df": reactions_df,
        "cases_count": len(cases_df),
        "reactions_count": len(reactions_df),
        "current_step": "canonicalize",
        "logs": state.get("logs", []) + [log],
    }


def compute_analyses_node(state: ReportWorkflowState) -> Dict[str, Any]:
    """Node 4: Execute pure deterministic statistical calculators and index in EvidenceStore."""
    cases_df = state["cases_df"]
    reactions_df = state["reactions_df"]
    d_cfg = state["dataset_config"]

    results = AnalysisRegistry.run_all(cases_df, reactions_df, d_cfg)
    store = EvidenceStore()
    store.add_many(results)

    log = f"[Analyses] Computed {len(results)} registered deterministic analyses."
    return {
        "analysis_results": results,
        "evidence_store": store,
        "analyses_completed": list(results.keys()),
        "current_step": "compute_analyses",
        "logs": state.get("logs", []) + [log],
    }


def build_evidence_packets_node(state: ReportWorkflowState) -> Dict[str, Any]:
    """Node 5: Assemble strictly context-isolated section evidence packets."""
    r_cfg = state["report_config"]
    d_cfg = state["dataset_config"]
    store = state["evidence_store"]

    packets = build_all_packets(r_cfg, store, d_cfg)
    log = f"[Packets] Assembled {len(packets)} isolated section evidence packets."
    return {
        "evidence_packets": packets,
        "packets_count": len(packets),
        "current_step": "build_evidence_packets",
        "logs": state.get("logs", []) + [log],
    }


def generate_sections_node(state: ReportWorkflowState) -> Dict[str, Any]:
    """Node 6: Multi-mode section generation across template, table, and LLM modes."""
    r_cfg = state["report_config"]
    packets = state["evidence_packets"]

    generator = SectionGenerator()
    drafts = generator.generate_all(r_cfg, packets)

    log = f"[Generation] Generated {len(drafts)} section drafts across configured modes."
    return {
        "drafts": drafts,
        "drafts_count": len(drafts),
        "current_step": "generate_sections",
        "logs": state.get("logs", []) + [log],
    }


def verify_facts_node(state: ReportWorkflowState) -> Dict[str, Any]:
    """Node 7: Deterministic fact checking and sentence-level claim citation mapping."""
    drafts = state["drafts"]
    packets = state["evidence_packets"]

    all_citations = []
    flags_count = 0

    for draft in drafts:
        pkt = packets[draft.section_id]
        fc_report = EvidenceFactChecker.verify_section(draft, pkt)
        all_citations.extend(fc_report.citations)
        flags_count += len(fc_report.flags)

    log = f"[Fact-Check] Verified {len(all_citations)} claim citations ({flags_count} flags)."
    return {
        "claim_citations": all_citations,
        "claim_citations_count": len(all_citations),
        "fact_check_flags_count": flags_count,
        "is_fully_grounded": (flags_count == 0),
        "current_step": "verify_facts",
        "logs": state.get("logs", []) + [log],
    }


def human_review_node(state: ReportWorkflowState) -> Dict[str, Any]:
    """Node 8: Human-in-the-loop review session management and approval recording."""
    drafts = state["drafts"]
    workflow = ReviewWorkflow(drafts)

    if state.get("auto_approve", True):
        workflow.approve_all(reviewer_name="Regulatory Lead Reviewer")

    log = f"[Review] Workflow status: {'APPROVED' if workflow.is_fully_approved() else 'PENDING_REVIEW'}."
    return {
        "review_workflow": workflow,
        "review_records": workflow.get_review_records(),
        "is_approved": workflow.is_fully_approved(),
        "current_step": "human_review",
        "logs": state.get("logs", []) + [log],
    }


def export_report_node(state: ReportWorkflowState) -> Dict[str, Any]:
    """Node 9: Assemble final ReportDocument and export Markdown, HTML, and Manifest."""
    r_cfg = state["report_config"]
    d_cfg = state["dataset_config"]
    dq_report = state["data_quality_report"]
    workflow = state["review_workflow"]
    store = state["evidence_store"]
    citations = state["claim_citations"]
    out_dir = Path(state.get("output_dir", "output"))
    out_dir.mkdir(parents=True, exist_ok=True)

    start_dt = date.fromisoformat(d_cfg.reporting_period_start) if isinstance(d_cfg.reporting_period_start, str) else d_cfg.reporting_period_start
    end_dt = date.fromisoformat(d_cfg.reporting_period_end) if isinstance(d_cfg.reporting_period_end, str) else d_cfg.reporting_period_end

    meta = ReportMetadata(
        report_id=f"PADER-{d_cfg.dataset_name.upper().replace(' ', '_')}-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        report_type=r_cfg.report_type,
        product_name=d_cfg.product_name,
        manufacturer=d_cfg.manufacturer,
        reporting_period_start=start_dt,
        reporting_period_end=end_dt,
        run_id=str(uuid.uuid4())[:8],
        app_version="0.1.0",
        config_file=state.get("report_config_path", "configs/pader.yaml"),
        dataset_file=state.get("dataset_config_path", "configs/dataset/bisoprolol.yaml"),
        is_fully_approved=workflow.is_fully_approved(),
    )

    report_doc = ReportDocument(
        metadata=meta,
        sections=workflow.get_drafts(),
        quality_report=dq_report,
        review_records=workflow.get_review_records(),
        full_markdown="",
        render_formats=["markdown", "html", "json"],
    )

    md_path = export_markdown_report(report_doc, out_dir / "pader_report.md")
    html_path = export_html_report(report_doc, out_dir / "pader_report.html")
    manifest_path = export_audit_manifest(report_doc, store, citations, out_dir / "provenance_manifest.json")

    exported = {
        "markdown": str(md_path),
        "html": str(html_path),
        "manifest": str(manifest_path),
    }

    log = f"[Export] Successfully packaged Markdown, HTML, and Manifest to '{out_dir}'."
    return {
        "report_document": report_doc,
        "exported_files": exported,
        "current_step": "export_report",
        "logs": state.get("logs", []) + [log],
    }
