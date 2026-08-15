"""Pytest fixtures for GenAR testing."""

import sys
from pathlib import Path
import pytest

# Ensure `src` is on sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def sample_report_config_path(project_root) -> Path:
    return project_root / "configs" / "pader.yaml"


@pytest.fixture(scope="session")
def sample_dataset_config_path(project_root) -> Path:
    return project_root / "configs" / "dataset" / "bisoprolol.yaml"
