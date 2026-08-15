"""Section drafts, generation modes, and verification statuses."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GenerationMode(str, Enum):
    TEMPLATE = "template"
    TABLE = "table"
    LLM = "llm"
    TABLE_AND_LLM = "table_and_llm"


class SectionDraft(BaseModel):
    """Represents a generated draft of a specific report section."""
    section_id: str
    title: str
    order: int
    generation_mode: GenerationMode
    markdown_content: str
    evidence_ids_used: List[str] = Field(default_factory=list)
    grounding_flags: List[str] = Field(default_factory=list)
    has_grounding_errors: bool = False
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    raw_response: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
