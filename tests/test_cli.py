"""Tests for CLI entrypoints and commands."""

from click.testing import CliRunner
from genar.cli import cli


def test_cli_help():
    """Verify genar --help returns clean exit and description."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "GenAR: Generative Adverse Event Reporting System" in result.output
    assert "validate-config" in result.output
    assert "inspect-data" in result.output
    assert "run-pipeline" in result.output


def test_cli_validate_config():
    """Verify validate-config command succeeds on default configs."""
    runner = CliRunner()
    result = runner.invoke(cli, ["validate-config"])
    assert result.exit_code == 0
    assert "All configuration files validated successfully" in result.output


def test_cli_inspect_data():
    """Verify inspect-data command executes and outputs dataset table."""
    runner = CliRunner()
    result = runner.invoke(cli, ["inspect-data"])
    assert result.exit_code == 0
    assert "Bisoprolol" in result.output
    assert "Aurobindo" in result.output
