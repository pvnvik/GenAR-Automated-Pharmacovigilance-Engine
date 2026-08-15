"""Command-line interface (CLI) for GenAR."""

from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from genar import __version__
from genar.config import load_dataset_config, load_report_config

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="genar")
def cli():
    """GenAR: Generative Adverse Event Reporting System.
    
    A deterministic core and evidence-backed regulatory safety report generator.
    """
    pass


@cli.command("validate-config")
@click.option(
    "--report-config",
    "-r",
    default="configs/pader.yaml",
    help="Path to report configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
def validate_config(report_config: str, dataset_config: str):
    """Validate report and dataset YAML configurations against Pydantic schemas."""
    console.print(Panel(f"[bold blue]GenAR Configuration Validator[/bold blue] (v{__version__})"))
    
    # Validate report config
    try:
        r_cfg = load_report_config(report_config)
        console.print(f"[green][OK][/green] Report Config Valid: [bold]{r_cfg.title}[/bold] ({len(r_cfg.sections)} sections defined)")
    except Exception as e:
        console.print(f"[red][ERROR][/red] Report Config Error: {e}")
        raise click.Abort()

    # Validate dataset config
    try:
        d_cfg = load_dataset_config(dataset_config)
        console.print(f"[green][OK][/green] Dataset Config Valid: [bold]{d_cfg.product_name}[/bold] (Manufacturer: {d_cfg.manufacturer})")
    except Exception as e:
        console.print(f"[red][ERROR][/red] Dataset Config Error: {e}")
        raise click.Abort()

    console.print("[bold green]All configuration files validated successfully![/bold green]")


@cli.command("inspect-data")
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
def inspect_data(dataset_config: str):
    """Inspect raw dataset path and configuration metadata without running pipeline."""
    cfg = load_dataset_config(dataset_config)
    data_path = Path(cfg.raw_data_path)
    
    table = Table(title=f"Dataset Configuration Overview: {cfg.product_name}")
    table.add_column("Property", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    table.add_row("Dataset Name", cfg.dataset_name)
    table.add_row("Product Name", cfg.product_name)
    table.add_row("Active Substance", cfg.active_substance)
    table.add_row("Manufacturer", cfg.manufacturer)
    table.add_row("Raw Data File", str(data_path))
    table.add_row("File Exists", str(data_path.exists()))
    if data_path.exists():
        table.add_row("File Size (KB)", f"{data_path.stat().st_size / 1024:.2f} KB")
    table.add_row("Reporting Period", f"{cfg.reporting_period_start} to {cfg.reporting_period_end}")
    table.add_row("Configured Age Buckets", str(len(cfg.age_buckets)))

    console.print(table)


@cli.command("validate-data")
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--output-report",
    "-o",
    default=None,
    help="Optional path to save data quality markdown report.",
    type=click.Path(),
)
def validate_data(dataset_config: str, output_report: Optional[str]):
    """Ingest raw dataset, run deterministic validation suite, and generate DQ report."""
    from genar.ingest.loader import create_dataset_metadata, load_raw_dataframe
    from genar.ingest.quality import build_data_quality_report, format_dq_summary_markdown
    from genar.ingest.validator import validate_dataset

    console.print(Panel(f"[bold blue]GenAR Data Ingestion & Quality Validator[/bold blue] (v{__version__})"))

    # 1. Load config
    cfg = load_dataset_config(dataset_config)
    console.print(f"[green][OK][/green] Loaded config for [bold]{cfg.product_name}[/bold]")

    # 2. Ingest raw data
    data_path = Path(cfg.raw_data_path)
    if not data_path.exists():
        console.print(f"[red][ERROR][/red] Raw data file not found: {data_path}")
        raise click.Abort()

    console.print(f"Ingesting raw dataset from [cyan]{data_path}[/cyan]...")
    df = load_raw_dataframe(data_path)
    metadata = create_dataset_metadata(df, cfg, data_path)
    console.print(f"[green][OK][/green] Ingested {len(df):,} rows ({metadata.total_canonical_cases:,} unique case IDs)")

    # 3. Run validation suite
    console.print("Executing deterministic validation suite...")
    issues = validate_dataset(df, cfg)
    dq_report = build_data_quality_report(issues, len(df), metadata.total_canonical_cases)

    # 4. Render Rich Summary Table
    table = Table(title="Data Quality Assessment Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold magenta")

    table.add_row("Total Raw Rows", f"{dq_report.total_raw_rows:,}")
    table.add_row("Unique Case IDs", f"{dq_report.total_unique_case_ids:,}")
    table.add_row("Duplicate/Updated Instances", f"{dq_report.duplicate_rows_detected}")
    table.add_row("Reaction/Outcome List Mismatches", f"{dq_report.list_mismatches_detected}")
    table.add_row("Critical Findings", f"{dq_report.critical_issues_count}")
    table.add_row("Warning Findings", f"{dq_report.warning_issues_count}")
    table.add_row("Info Findings", f"{dq_report.info_issues_count}")

    console.print(table)

    if dq_report.summary_by_type:
        type_table = Table(title="Findings by Category")
        type_table.add_column("Issue Type", style="yellow")
        type_table.add_column("Count", style="bold white")
        for itype, count in sorted(dq_report.summary_by_type.items(), key=lambda x: x[1], reverse=True):
            type_table.add_row(itype, str(count))
        console.print(type_table)

    # 5. Export Report if requested
    if output_report:
        out_path = Path(output_report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        md_text = format_dq_summary_markdown(dq_report)
        out_path.write_text(md_text, encoding="utf-8")
        console.print(f"[bold green]Data quality markdown report saved to {out_path}[/bold green]")


@cli.command("canonicalize")
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
    type=click.Path(exists=True),
)
@click.option(
    "--output-dir",
    "-o",
    default="data/processed",
    help="Directory to save canonical cases and reactions CSV artifacts.",
    type=click.Path(),
)
def canonicalize(dataset_config: str, output_dir: str):
    """Run deduplication and build canonical case-level and exploded reaction-level tables."""
    from genar.ingest.canonicalizer import run_canonicalization
    from genar.ingest.loader import load_raw_dataframe

    console.print(Panel(f"[bold blue]GenAR Dataset Canonicalizer[/bold blue] (v{__version__})"))

    cfg = load_dataset_config(dataset_config)
    console.print(f"[green][OK][/green] Loaded dataset config for [bold]{cfg.product_name}[/bold]")

    raw_path = Path(cfg.raw_data_path)
    if not raw_path.exists():
        console.print(f"[red][ERROR][/red] Raw data file not found: {raw_path}")
        raise click.Abort()

    console.print(f"Loading raw dataset from [cyan]{raw_path}[/cyan]...")
    raw_df = load_raw_dataframe(raw_path)

    console.print("Executing canonicalization (deduplication + reaction explosion)...")
    cases_df, reactions_df, result = run_canonicalization(raw_df, cfg, output_dir=output_dir)

    table = Table(title="Canonicalization Summary")
    table.add_column("Analytical View", style="cyan")
    table.add_column("Count", style="bold magenta")
    table.add_column("Artifact File Path", style="green")

    table.add_row(
        "Canonical Cases (1 per case ID)",
        f"{result.total_canonical_cases:,}",
        str(result.cases_file_path),
    )
    table.add_row(
        "Exploded Reactions (1 per event)",
        f"{result.total_exploded_reactions:,}",
        str(result.reactions_file_path),
    )
    table.add_row(
        "  - Positionally Aligned Reactions",
        f"{result.aligned_reactions_count:,}",
        "-",
    )
    table.add_row(
        "  - Unaligned Reactions (Flagged)",
        f"{result.unaligned_reactions_count:,}",
        "-",
    )

    console.print(table)
    console.print("[bold green]Canonicalization complete and artifacts successfully persisted![/bold green]")


@cli.command("run-pipeline")
@click.option(
    "--report-config",
    "-r",
    default="configs/pader.yaml",
    help="Path to report configuration YAML file.",
)
@click.option(
    "--dataset-config",
    "-d",
    default="configs/dataset/bisoprolol.yaml",
    help="Path to dataset configuration YAML file.",
)
def run_pipeline(report_config: str, dataset_config: str):
    """Execute the deterministic analysis and evidence pipeline (Phase 3+)."""
    console.print("[yellow]Deterministic pipeline execution will be implemented in subsequent phases (Phase 4-10).[/yellow]")


if __name__ == "__main__":
    cli()
