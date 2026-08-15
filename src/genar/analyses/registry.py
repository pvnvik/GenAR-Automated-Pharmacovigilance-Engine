"""Deterministic analysis registry for registering, resolving, and running analyses."""

import functools
import importlib
import inspect
import time
from typing import Any, Callable, Dict, List, Optional
import pandas as pd

from genar.config import DatasetConfig
from genar.models.analysis import AnalysisCategory, AnalysisResult


class AnalysisRegistry:
    """Registry mapping analysis identifiers to deterministic calculation functions."""
    
    _registry: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        category: AnalysisCategory,
        description: str,
        version: str = "1.0",
    ):
        """Decorator to register a calculation function."""
        def decorator(func: Callable):
            cls._registry[name] = {
                "name": name,
                "func": func,
                "category": category,
                "description": description,
                "version": version,
                "method_name": f"{func.__module__}.{func.__name__}",
            }
            return func
        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[Dict[str, Any]]:
        """Retrieve registered analysis metadata and function by name."""
        cls._ensure_loaded()
        return cls._registry.get(name)

    @classmethod
    def list_analyses(cls) -> List[Dict[str, Any]]:
        """List all registered analyses."""
        cls._ensure_loaded()
        return [
            {
                "name": k,
                "category": v["category"].value,
                "description": v["description"],
                "version": v["version"],
                "method_name": v["method_name"],
            }
            for k, v in cls._registry.items()
        ]

    @classmethod
    def run_analysis(
        cls,
        name: str,
        cases_df: pd.DataFrame,
        reactions_df: pd.DataFrame,
        config: DatasetConfig,
        **kwargs
    ) -> AnalysisResult:
        """Execute a registered analysis and return an AnalysisResult with provenance."""
        cls._ensure_loaded()
        entry = cls._registry.get(name)
        if not entry:
            raise KeyError(f"Analysis '{name}' is not registered. Registered: {list(cls._registry.keys())}")

        func = entry["func"]
        start_time = time.perf_counter()
        
        # Invoke calculation function
        metrics, contributing_cases = func(cases_df, reactions_df, config, **kwargs)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return AnalysisResult(
            analysis_id=name,
            version=entry["version"],
            name=name,
            description=entry["description"],
            category=entry["category"],
            dataset_id=config.dataset_name,
            parameters=kwargs,
            metrics=metrics,
            contributing_case_ids=contributing_cases,
            execution_time_ms=round(elapsed_ms, 3),
            method_name=entry["method_name"],
        )

    @classmethod
    def run_all(
        cls,
        cases_df: pd.DataFrame,
        reactions_df: pd.DataFrame,
        config: DatasetConfig,
    ) -> Dict[str, AnalysisResult]:
        """Execute all registered analyses and return dictionary of results."""
        cls._ensure_loaded()
        results: Dict[str, AnalysisResult] = {}
        for name in list(cls._registry.keys()):
            results[name] = cls.run_analysis(name, cases_df, reactions_df, config)
        return results

    @classmethod
    def _ensure_loaded(cls):
        """Import all built-in analysis modules once so decorators execute."""
        modules = [
            "genar.analyses.volume",
            "genar.analyses.seriousness",
            "genar.analyses.demographics",
            "genar.analyses.reactions",
            "genar.analyses.outcomes",
            "genar.analyses.alerts",
            "genar.analyses.trends",
        ]
        for mod in modules:
            try:
                importlib.import_module(mod)
            except ImportError:
                pass


register_analysis = AnalysisRegistry.register
