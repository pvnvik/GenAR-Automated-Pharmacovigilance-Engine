"""Raw data ingestion and file loader preserving original source records."""

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from genar.config import ColumnMappingConfig, DatasetConfig
from genar.models.dataset import DatasetMetadata, RawCaseRecord


def calculate_file_checksum(file_path: str | Path) -> str:
    """Compute SHA-256 checksum of a raw data file for provenance."""
    path = Path(file_path)
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def load_raw_dataframe(file_path: str | Path) -> pd.DataFrame:
    """Load raw dataset (CSV or XLSX) into a Pandas DataFrame without destructive transformations."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Raw data file not found: {path}")

    suffix = path.suffix.lower()
    if suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    elif suffix in [".csv", ".tsv"]:
        sep = "\t" if suffix == ".tsv" else ","
        df = pd.read_csv(path, sep=sep, low_memory=False)
    else:
        raise ValueError(f"Unsupported file format '{suffix}'. Supported formats: .xlsx, .xls, .csv, .tsv")

    return df


def to_raw_case_records(
    df: pd.DataFrame,
    mapping: Optional[ColumnMappingConfig] = None
) -> List[RawCaseRecord]:
    """Convert raw DataFrame rows into structured RawCaseRecord domain models."""
    mapping = mapping or ColumnMappingConfig()
    records: List[RawCaseRecord] = []

    for idx, row in df.iterrows():
        raw_dict = row.to_dict()
        
        # Extract safety report ID
        case_id_val = row.get(mapping.case_id)
        safety_report_id = str(int(case_id_val)) if isinstance(case_id_val, (int, float)) and pd.notna(case_id_val) else str(case_id_val or f"UNKNOWN_ROW_{idx}")
        
        # Extract age
        age_val = row.get(mapping.patient_age)
        patient_age = float(age_val) if pd.notna(age_val) and isinstance(age_val, (int, float, str)) and str(age_val).replace('.', '', 1).isdigit() else None

        record = RawCaseRecord(
            raw_row_id=int(idx),
            safety_report_id=safety_report_id,
            received_date=None,  # parsed in validator / canonicalizer
            receipt_date=None,
            patient_sex=str(row.get(mapping.patient_sex)) if pd.notna(row.get(mapping.patient_sex)) else None,
            patient_age=patient_age,
            patient_age_group=str(row.get("patient_patientagegroup")) if pd.notna(row.get("patient_patientagegroup")) else None,
            primary_source_country=str(row.get(mapping.country)) if pd.notna(row.get(mapping.country)) else None,
            reaction_meddra_pt=str(row.get(mapping.reactions_pt)) if pd.notna(row.get(mapping.reactions_pt)) else None,
            reaction_outcome=str(row.get(mapping.reactions_outcome)) if pd.notna(row.get(mapping.reactions_outcome)) else None,
            drug_characterization=str(row.get(mapping.drug_characterization)) if pd.notna(row.get(mapping.drug_characterization)) else None,
            medicinal_product=str(row.get(mapping.drugs)) if pd.notna(row.get(mapping.drugs)) else None,
            raw_fields=raw_dict,
        )
        records.append(record)

    return records


def create_dataset_metadata(
    df: pd.DataFrame,
    config: DatasetConfig,
    file_path: str | Path
) -> DatasetMetadata:
    """Construct initial DatasetMetadata from raw DataFrame and config."""
    path = Path(file_path)
    id_col = config.column_mapping.case_id
    total_unique = df[id_col].nunique() if id_col in df.columns else len(df)
    checksum = calculate_file_checksum(path) if path.exists() else None

    return DatasetMetadata(
        dataset_name=config.dataset_name,
        file_path=str(path),
        total_raw_rows=len(df),
        total_canonical_cases=int(total_unique),
        total_reactions=0,  # calculated during canonicalization
        checksum=checksum,
    )
