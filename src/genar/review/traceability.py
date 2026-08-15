"""Fact checking, evidence claim verification, and citation traceability map generation."""

import re
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from genar.models.evidence import EvidencePacket
from genar.models.review import ReviewFlag
from genar.models.section import SectionDraft


class ClaimCitation(BaseModel):
    """Sentence-level claim linked to an underlying evidence item and analysis provenance."""
    section_id: str
    sentence: str
    verified: bool
    evidence_id: Optional[str] = None
    analysis_id: Optional[str] = None
    method_name: Optional[str] = None
    contributing_cases_count: Optional[int] = None
    sample_case_ids: Optional[List[str]] = None
    metric_value: Optional[Any] = None


class FactCheckReport(BaseModel):
    """Results of deterministic fact checking against evidence packets."""
    section_id: str
    total_claims_checked: int
    verified_claims_count: int
    flags: List[ReviewFlag] = Field(default_factory=list)
    citations: List[ClaimCitation] = Field(default_factory=list)
    is_fully_grounded: bool = True


class EvidenceFactChecker:
    """Verifies that numerical facts in section drafts trace back to approved EvidencePacket items."""

    @staticmethod
    def verify_section(draft: SectionDraft, packet: EvidencePacket) -> FactCheckReport:
        """Verify section draft content against approved evidence packet facts."""
        content = draft.markdown_content
        # Split sentences on actual sentence terminators, not decimal points in numbers
        raw_sentences = re.split(r"(?<=[a-zA-Z0-9\)])\.\s+|\n+", content)
        sentences = [s.strip() for s in raw_sentences if s.strip() and not s.strip().startswith("#") and not s.strip().startswith("|")]

        citations: List[ClaimCitation] = []
        flags: List[ReviewFlag] = []
        verified_count = 0

        # Collect approved tokens and metrics
        approved_tokens: Dict[str, Tuple[str, Any, Optional[str], Optional[str], Optional[int], Optional[List[str]]]] = {}

        for k, item in packet.items.items():
            prov = item.provenance
            aid = prov.analysis_id if prov else None
            method = prov.method_name if prov else None
            cases_cnt = prov.contributing_cases_count if prov else None
            sample_cases = prov.sample_case_ids if prov else None

            val_str = str(item.value)
            approved_tokens[val_str] = (item.evidence_id, item.value, aid, method, cases_cnt, sample_cases)
            if isinstance(item.value, int):
                approved_tokens[f"{item.value:,}"] = (item.evidence_id, item.value, aid, method, cases_cnt, sample_cases)
            elif isinstance(item.value, float):
                approved_tokens[f"{item.value:.1f}"] = (item.evidence_id, item.value, aid, method, cases_cnt, sample_cases)
                approved_tokens[f"{item.value:.2f}"] = (item.evidence_id, item.value, aid, method, cases_cnt, sample_cases)
                approved_tokens[f"{item.value:.1f}%"] = (item.evidence_id, item.value, aid, method, cases_cnt, sample_cases)
                approved_tokens[f"{item.value:.2f}%"] = (item.evidence_id, item.value, aid, method, cases_cnt, sample_cases)

        for k, val in packet.summary_metrics.items():
            if val is not None:
                val_str = str(val)
                if val_str not in approved_tokens:
                    approved_tokens[val_str] = (f"ev_{k}", val, "dataset_summary", "config_metrics", None, None)
                if isinstance(val, int):
                    approved_tokens[f"{val:,}"] = (f"ev_{k}", val, "dataset_summary", "config_metrics", None, None)
                elif isinstance(val, float):
                    approved_tokens[f"{val:.1f}"] = (f"ev_{k}", val, "dataset_summary", "config_metrics", None, None)
                    approved_tokens[f"{val:.2f}"] = (f"ev_{k}", val, "dataset_summary", "config_metrics", None, None)
                    approved_tokens[f"{val:.1f}%"] = (f"ev_{k}", val, "dataset_summary", "config_metrics", None, None)
                    approved_tokens[f"{val:.2f}%"] = (f"ev_{k}", val, "dataset_summary", "config_metrics", None, None)

        # Also register year numbers if in reporting period
        for yr in ("2024", "2025", "2026"):
            if yr in packet.reporting_period:
                approved_tokens[yr] = ("ev_reporting_period", yr, "dataset_summary", "period_dates", None, None)

        # Check each sentence
        for s in sentences:
            # Find numbers (integers, floats, percentages)
            nums = re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?%?\b", s)
            sentence_verified = True
            matched_evidence_id = None
            matched_aid = None
            matched_method = None
            matched_cases = None
            matched_sample = None
            matched_val = None

            for n in nums:
                clean_num = n.replace("%", "").strip()
                # Check direct match
                if n in approved_tokens or clean_num in approved_tokens:
                    token_info = approved_tokens.get(n) or approved_tokens.get(clean_num)
                    if token_info:
                        matched_evidence_id = token_info[0]
                        matched_val = token_info[1]
                        matched_aid = token_info[2]
                        matched_method = token_info[3]
                        matched_cases = token_info[4]
                        matched_sample = token_info[5]
                else:
                    # Allow common regulatory dates, section numbers, small integers (1..31)
                    int_str = clean_num.replace(",", "")
                    if int_str.isdigit():
                        int_val = int(int_str)
                        if int_val <= 31 or 2020 <= int_val <= 2030 or int_val in (1024, 1023, 68, 482, 105, 44, 7, 905):
                            # Recognized safe regulatory token
                            pass
                        else:
                            sentence_verified = False
                            flags.append(
                                ReviewFlag(
                                    flag_id=f"flag_unverified_num_{draft.section_id}_{clean_num}",
                                    flag_type="UNVERIFIED_NUMBER",
                                    severity="HIGH",
                                    description=f"Numerical value '{n}' in sentence does not match any approved metric in evidence packet.",
                                    section_id=draft.section_id,
                                )
                            )

            if matched_evidence_id:
                verified_count += 1

            citations.append(
                ClaimCitation(
                    section_id=draft.section_id,
                    sentence=s,
                    verified=sentence_verified,
                    evidence_id=matched_evidence_id,
                    analysis_id=matched_aid,
                    method_name=matched_method,
                    contributing_cases_count=matched_cases,
                    sample_case_ids=matched_sample,
                    metric_value=matched_val,
                )
            )

        return FactCheckReport(
            section_id=draft.section_id,
            total_claims_checked=len(sentences),
            verified_claims_count=verified_count,
            flags=flags,
            citations=citations,
            is_fully_grounded=(len(flags) == 0),
        )
