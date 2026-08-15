"""Evidence store for indexing, managing, and retrieving analysis results and verified facts."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from genar.models.analysis import AnalysisResult
from genar.models.evidence import EvidenceItem, EvidenceProvenance


class EvidenceStore:
    """Store holding deterministic AnalysisResult objects and serving traceable EvidenceItems."""

    def __init__(self):
        self._store: Dict[str, AnalysisResult] = {}

    def add(self, result: AnalysisResult) -> None:
        """Add an AnalysisResult to the store."""
        self._store[result.analysis_id] = result

    def add_many(self, results: Dict[str, AnalysisResult]) -> None:
        """Add multiple AnalysisResults to the store."""
        self._store.update(results)

    def get(self, analysis_id: str) -> Optional[AnalysisResult]:
        """Retrieve AnalysisResult by ID."""
        return self._store.get(analysis_id)

    def list_analyses(self) -> List[str]:
        """Return list of all stored analysis IDs."""
        return list(self._store.keys())

    def get_provenance(self, analysis_id: str) -> Optional[EvidenceProvenance]:
        """Extract provenance metadata from an analysis result."""
        res = self.get(analysis_id)
        if not res:
            return None

        contributing_count = len(res.contributing_case_ids) if res.contributing_case_ids else None
        sample_cases = res.contributing_case_ids[:5] if res.contributing_case_ids else None

        return EvidenceProvenance(
            analysis_id=res.analysis_id,
            version=res.version,
            category=res.category.value,
            calculated_at=res.calculated_at,
            method_name=res.method_name,
            contributing_cases_count=contributing_count,
            sample_case_ids=sample_cases,
        )

    def create_evidence_item(
        self,
        evidence_id: str,
        title: str,
        metric_key: str,
        analysis_id: str,
        value: Any,
        formatted_value: str,
        description: Optional[str] = None,
        table_representation: Optional[List[Dict[str, Any]]] = None,
    ) -> EvidenceItem:
        """Construct an EvidenceItem with strict provenance linking back to analysis."""
        prov = self.get_provenance(analysis_id)
        if not prov:
            raise KeyError(f"Cannot create evidence item '{evidence_id}': Analysis '{analysis_id}' not found in store.")

        return EvidenceItem(
            evidence_id=evidence_id,
            title=title,
            metric_key=metric_key,
            value=value,
            formatted_value=formatted_value,
            provenance=prov,
            description=description,
            table_representation=table_representation,
        )

    def save_to_json(self, file_path: str | Path) -> None:
        """Persist all stored analysis results to a JSON file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        dump_data = {k: v.model_dump(mode="json") for k, v in self._store.items()}
        path.write_text(json.dumps(dump_data, indent=2, default=str), encoding="utf-8")

    @classmethod
    def load_from_json(cls, file_path: str | Path) -> "EvidenceStore":
        """Instantiate EvidenceStore from a saved JSON file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Evidence store file not found: {path}")

        data = json.loads(path.read_text(encoding="utf-8"))
        store = cls()
        for k, v in data.items():
            store.add(AnalysisResult(**v))
        return store
