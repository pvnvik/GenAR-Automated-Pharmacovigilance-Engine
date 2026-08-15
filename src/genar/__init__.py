"""
GenAR: Generative Adverse Event Reporting System
Deterministic core and evidence-backed regulatory report generator.
"""

import os
from pathlib import Path

# Automatically load .env file if available
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).resolve().parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()
except ImportError:
    pass

__version__ = "0.1.0"
