"""Configuration models and YAML loader for GenAR reports and datasets."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, ValidationError


class SectionConfig(BaseModel):
    """Configuration for a specific report section."""
    id: str
    title: str
    order: int
    generation_mode: str = "template"  # template, table, llm, table_and_llm
    required_evidence: List[str] = Field(default_factory=list)
    template: Optional[str] = None
    prompt_template: Optional[str] = None
    table_columns: Optional[List[str]] = None
    non_invention_rules: List[str] = Field(default_factory=list)
    description: Optional[str] = None


class ReportConfig(BaseModel):
    """Report template and section ordering configuration."""
    report_type: str = "PADER"
    title: str
    version: str = "1.0"
    regulatory_framework: str = "FDA PADER (21 CFR 314.80)"
    sections: List[SectionConfig] = Field(default_factory=list)


class AgeBucketConfig(BaseModel):
    """Configurable age bucket definition."""
    label: str
    min_age: float
    max_age: Optional[float] = None


class ColumnMappingConfig(BaseModel):
    """Column mapping from raw data to standard schema."""
    case_id: str = "safetyreportid"
    version: str = "safetyreportversion"
    received_date: str = "receivedate"
    receipt_date: str = "receiptdate"
    serious: str = "serious"
    serious_death: str = "seriousnessdeath"
    serious_lifethreatening: str = "seriousnesslifethreatening"
    serious_hospitalization: str = "seriousnesshospitalization"
    serious_disabling: str = "seriousnessdisabling"
    serious_congenital: str = "seriousnesscongenitalanomali"
    serious_other: str = "seriousnessother"
    patient_sex: str = "patient_patientsex"
    patient_age: str = "patient_patientonsetage"
    patient_age_unit: str = "patient_patientonsetageunit"
    country: str = "primarysourcecountry"
    reactions_pt: str = "patient_reaction_reactionmeddrapt"
    reactions_outcome: str = "patient_reaction_reactionoutcome"
    drugs: str = "patient_drug_medicinalproduct"
    drug_characterization: str = "patient_drug_drugcharacterization"
    active_substance: str = "patient_drug_activesubstance_activesubstancename"
    expedited_15day: str = "fulfillexpeditecriteria"


class DatasetRulesConfig(BaseModel):
    """Assumptions and rules for dataset canonicalization."""
    list_delimiter: str = ","
    deduplication_policy: str = "LATEST_VERSION"  # LATEST_VERSION, FIRST_SEEN, MERGE_AND_FLAG
    date_format_code: int = 102  # YYYYMMDD
    unknown_country_label: str = "UNKNOWN"
    unknown_sex_label: str = "UNKNOWN"
    flag_positional_mismatches: bool = True


class DatasetConfig(BaseModel):
    """Dataset configuration including product metadata and column mappings."""
    dataset_name: str
    product_name: str
    active_substance: str
    manufacturer: str
    raw_data_path: str
    reporting_period_start: str
    reporting_period_end: str
    column_mapping: ColumnMappingConfig = Field(default_factory=ColumnMappingConfig)
    age_buckets: List[AgeBucketConfig] = Field(default_factory=list)
    rules: DatasetRulesConfig = Field(default_factory=DatasetRulesConfig)
    assumptions: List[str] = Field(default_factory=list)


def load_yaml(file_path: str | Path) -> Dict[str, Any]:
    """Safely load raw YAML from a file path."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def load_report_config(file_path: str | Path) -> ReportConfig:
    """Load and validate ReportConfig from a YAML file."""
    data = load_yaml(file_path)
    try:
        return ReportConfig(**data)
    except ValidationError as e:
        raise ValueError(f"Invalid ReportConfig in {file_path}: {e}") from e


def load_dataset_config(file_path: str | Path) -> DatasetConfig:
    """Load and validate DatasetConfig from a YAML file."""
    data = load_yaml(file_path)
    try:
        return DatasetConfig(**data)
    except ValidationError as e:
        raise ValueError(f"Invalid DatasetConfig in {file_path}: {e}") from e
