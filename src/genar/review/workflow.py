"""Human review workflow, section review states, approval tracking, and revision loop."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from genar.config import SectionConfig
from genar.generation.dispatcher import SectionGenerator
from genar.models.evidence import EvidencePacket
from genar.models.review import ReviewFlag, ReviewRecord, ReviewStatus
from genar.models.section import SectionDraft


class ReviewWorkflow:
    """Manages human reviewer interactions, approval states, and feedback loops."""

    def __init__(self, drafts: List[SectionDraft]):
        self._drafts: Dict[str, SectionDraft] = {d.section_id: d for d in drafts}
        self._records: Dict[str, ReviewRecord] = {}

        # Initialize review records
        for d in drafts:
            self._records[d.section_id] = ReviewRecord(
                review_id=f"rev_{d.section_id}",
                section_id=d.section_id,
                status=ReviewStatus.PENDING_REVIEW,
                approved_content=None,
            )

    def approve_section(
        self,
        section_id: str,
        reviewer_name: str = "Lead Safety Reviewer",
        comments: Optional[str] = None,
    ) -> ReviewRecord:
        """Approve a section draft and record human reviewer stamp."""
        record = self._records.get(section_id)
        if not record:
            raise KeyError(f"Section '{section_id}' not found in review session.")

        record.status = ReviewStatus.APPROVED
        record.reviewer_name = reviewer_name
        record.reviewed_at = datetime.now(timezone.utc)
        if comments:
            record.comments.append(comments)
        record.approved_content = self._drafts[section_id].markdown_content
        return record

    def reject_section(
        self,
        section_id: str,
        reviewer_name: str,
        reason: str,
        flags: Optional[List[ReviewFlag]] = None,
    ) -> ReviewRecord:
        """Reject a section draft and attach review flags or revision requests."""
        record = self._records.get(section_id)
        if not record:
            raise KeyError(f"Section '{section_id}' not found in review session.")

        record.status = ReviewStatus.REJECTED
        record.reviewer_name = reviewer_name
        record.reviewed_at = datetime.now(timezone.utc)
        record.comments.append(f"REJECTION REASON: {reason}")
        if flags:
            record.flags.extend(flags)
        return record

    def add_comment(self, section_id: str, comment: str) -> None:
        """Attach a review note or comment to a section."""
        record = self._records.get(section_id)
        if not record:
            raise KeyError(f"Section '{section_id}' not found in review session.")
        record.comments.append(comment)

    def regenerate_section(
        self,
        section_id: str,
        section_cfg: SectionConfig,
        packet: EvidencePacket,
        generator: SectionGenerator,
        guidance: Optional[str] = None,
    ) -> SectionDraft:
        """Regenerate a rejected or revised section using feedback guidance."""
        if guidance:
            self.add_comment(section_id, f"Regeneration guidance provided: {guidance}")

        new_draft = generator.generate_section(section_cfg, packet)
        self._drafts[section_id] = new_draft

        # Update review record
        record = self._records[section_id]
        record.status = ReviewStatus.PENDING_REVIEW
        record.approved_content = None
        record.comments.append(f"Regenerated at {datetime.now(timezone.utc).isoformat()}")

        return new_draft

    def approve_all(self, reviewer_name: str = "Lead Safety Reviewer") -> None:
        """Convenience method to approve all sections."""
        for sid in self._drafts.keys():
            self.approve_section(sid, reviewer_name=reviewer_name)

    def is_fully_approved(self) -> bool:
        """Return True only if all sections in the report have been approved."""
        return all(r.status == ReviewStatus.APPROVED for r in self._records.values())

    def get_review_records(self) -> List[ReviewRecord]:
        """Return all review records in the session."""
        return list(self._records.values())

    def get_drafts(self) -> List[SectionDraft]:
        """Return current section drafts."""
        return list(self._drafts.values())
