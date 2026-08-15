"""LangGraph state schema and typing definitions for GenAR workflow orchestration."""

from typing import Any, Dict, List, Optional, Tuple, TypedDict


class ReportWorkflowState(TypedDict, total=False):
    """Unified state dictionary passed between nodes in the LangGraph workflow."""

    # Input parameters
    report_config_path: str
    dataset_config_path: str
    output_dir: str
    auto_approve: bool

    # Configurations
    report_config: Optional[Any]
    dataset_config: Optional[Any]

    # Dataframes & Ingestion
    raw_df: Optional[Any]
    raw_data_shape: Optional[Tuple[int, int]]
    data_quality_report: Optional[Any]
    dq_issues_count: int

    # Canonicalization
    cases_df: Optional[Any]
    reactions_df: Optional[Any]
    cases_count: int
    reactions_count: int

    # Analyses & Evidence Store
    analysis_results: Dict[str, Any]
    evidence_store: Optional[Any]
    analyses_completed: List[str]

    # Evidence Packets
    evidence_packets: Dict[str, Any]
    packets_count: int

    # Generation & Drafts
    drafts: List[Any]
    drafts_count: int

    # Verification & Citations
    fact_check_flags_count: int
    claim_citations_count: int
    claim_citations: List[Any]
    is_fully_grounded: bool

    # Human Review
    review_workflow: Optional[Any]
    review_records: List[Any]
    is_approved: bool

    # Assembled Report & Export Paths
    report_document: Optional[Any]
    exported_files: Dict[str, str]

    # Workflow Metadata & Logging
    current_step: str
    logs: List[str]
    error: Optional[str]
