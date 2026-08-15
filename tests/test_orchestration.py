"""Unit and integration tests for LangGraph state machine, nodes, and compiled workflow."""

from pathlib import Path
import pytest
from click.testing import CliRunner

from genar.cli import cli
from genar.orchestration.graph import (
    create_genar_workflow,
    run_orchestrated_pipeline,
)
from genar.orchestration.nodes import (
    canonicalize_node,
    compute_analyses_node,
    ingest_validate_node,
    load_configs_node,
)
from genar.orchestration.state import ReportWorkflowState


def test_workflow_graph_compilation():
    """Verify LangGraph StateGraph builds and compiles with all nodes and edges."""
    graph = create_genar_workflow()
    assert graph is not None
    assert hasattr(graph, "invoke")


def test_individual_node_execution(sample_report_config_path: Path, sample_dataset_config_path: Path):
    """Verify sequential execution of individual node functions."""
    # 1. Load configs node
    state: ReportWorkflowState = {
        "report_config_path": str(sample_report_config_path),
        "dataset_config_path": str(sample_dataset_config_path),
        "logs": [],
    }
    s1 = load_configs_node(state)
    state.update(s1)
    assert state["report_config"] is not None
    assert state["dataset_config"] is not None
    assert state["current_step"] == "load_configs"

    # 2. Ingest and validate node
    s2 = ingest_validate_node(state)
    state.update(s2)
    assert state["raw_df"] is not None
    assert state["raw_data_shape"][0] == 1068
    assert state["dq_issues_count"] == 47

    # 3. Canonicalize node
    s3 = canonicalize_node(state)
    state.update(s3)
    assert state["cases_count"] == 1024
    assert state["reactions_count"] == 3429

    # 4. Compute analyses node
    s4 = compute_analyses_node(state)
    state.update(s4)
    assert len(state["analyses_completed"]) == 7
    assert "total_case_volume" in state["analyses_completed"]


def test_run_orchestrated_pipeline_full(tmp_path: Path, sample_report_config_path: Path, sample_dataset_config_path: Path):
    """Verify full end-to-end execution of compiled LangGraph workflow."""
    out_dir = tmp_path / "graph_output"
    final_state = run_orchestrated_pipeline(
        report_config_path=str(sample_report_config_path),
        dataset_config_path=str(sample_dataset_config_path),
        output_dir=str(out_dir),
        auto_approve=True,
    )

    assert final_state["current_step"] == "export_report"
    assert final_state["cases_count"] == 1024
    assert final_state["reactions_count"] == 3429
    assert len(final_state["analyses_completed"]) == 7
    assert final_state["packets_count"] == 8
    assert final_state["drafts_count"] == 8
    assert final_state["is_approved"] is True
    assert len(final_state["logs"]) >= 9

    # Check exported artifacts
    exported = final_state["exported_files"]
    assert Path(exported["markdown"]).exists()
    assert Path(exported["html"]).exists()
    assert Path(exported["manifest"]).exists()


def test_cli_run_graph_command(tmp_path: Path):
    """Verify CLI run-graph command executes the compiled LangGraph workflow."""
    runner = CliRunner()
    out_dir = tmp_path / "cli_graph_output"
    result = runner.invoke(cli, ["run-graph", "-o", str(out_dir)])

    assert result.exit_code == 0
    assert "GenAR LangGraph Workflow Orchestrator" in result.output
    assert "LangGraph Workflow Completed Successfully!" in result.output
    assert (out_dir / "pader_report.md").exists()
    assert (out_dir / "pader_report.html").exists()
    assert (out_dir / "provenance_manifest.json").exists()
