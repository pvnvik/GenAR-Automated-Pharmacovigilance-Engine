"""StateGraph builder, conditional edges, and compiled workflow for GenAR."""

from typing import Any, Dict, Optional
from langgraph.graph import END, START, StateGraph

from genar.orchestration.nodes import (
    build_evidence_packets_node,
    canonicalize_node,
    compute_analyses_node,
    export_report_node,
    generate_sections_node,
    human_review_node,
    ingest_validate_node,
    load_configs_node,
    verify_facts_node,
)
from genar.orchestration.state import ReportWorkflowState


def create_genar_workflow() -> Any:
    """Construct and compile the full LangGraph state machine for GenAR."""
    builder = StateGraph(ReportWorkflowState)

    # 1. Add all workflow nodes
    builder.add_node("load_configs", load_configs_node)
    builder.add_node("ingest_validate", ingest_validate_node)
    builder.add_node("canonicalize", canonicalize_node)
    builder.add_node("compute_analyses", compute_analyses_node)
    builder.add_node("build_evidence_packets", build_evidence_packets_node)
    builder.add_node("generate_sections", generate_sections_node)
    builder.add_node("verify_facts", verify_facts_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("export_report", export_report_node)

    # 2. Add sequential pipeline edges
    builder.add_edge(START, "load_configs")
    builder.add_edge("load_configs", "ingest_validate")
    builder.add_edge("ingest_validate", "canonicalize")
    builder.add_edge("canonicalize", "compute_analyses")
    builder.add_edge("compute_analyses", "build_evidence_packets")
    builder.add_edge("build_evidence_packets", "generate_sections")
    builder.add_edge("generate_sections", "verify_facts")
    builder.add_edge("verify_facts", "human_review")
    builder.add_edge("human_review", "export_report")
    builder.add_edge("export_report", END)

    # 3. Compile the graph
    return builder.compile()


def run_orchestrated_pipeline(
    report_config_path: str = "configs/pader.yaml",
    dataset_config_path: str = "configs/dataset/bisoprolol.yaml",
    output_dir: str = "output",
    auto_approve: bool = True,
) -> ReportWorkflowState:
    """Execute the full compiled LangGraph workflow from initial state to exported artifacts."""
    graph = create_genar_workflow()
    initial_state: ReportWorkflowState = {
        "report_config_path": report_config_path,
        "dataset_config_path": dataset_config_path,
        "output_dir": output_dir,
        "auto_approve": auto_approve,
        "logs": [],
        "analyses_completed": [],
    }

    final_state = graph.invoke(initial_state)
    return final_state
