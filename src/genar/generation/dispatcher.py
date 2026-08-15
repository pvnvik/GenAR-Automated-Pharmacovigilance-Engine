"""Section generator and dispatching engine across template, table, and LLM modes."""

from typing import Dict, List, Optional
from genar.config import ReportConfig, SectionConfig
from genar.generation.llm import LLMGenerator
from genar.generation.tables import render_table_section
from genar.generation.templates import render_template_section
from genar.models.evidence import EvidencePacket
from genar.models.section import GenerationMode, SectionDraft


class SectionGenerator:
    """Dispatches section generation to template, table, or LLM renderers based on configuration."""

    def __init__(self, llm_generator: Optional[LLMGenerator] = None):
        self.llm = llm_generator or LLMGenerator()

    def generate_section(
        self,
        section_cfg: SectionConfig,
        packet: EvidencePacket,
    ) -> SectionDraft:
        """Generate a single report section draft according to its configured generation_mode."""
        mode_str = section_cfg.generation_mode.lower()
        evidence_ids = [item.evidence_id for item in packet.items.values()]

        # 1. Template Mode
        if mode_str == "template":
            content = render_template_section(section_cfg, packet)
            gen_mode = GenerationMode.TEMPLATE

        # 2. Table Mode
        elif mode_str == "table":
            content = render_table_section(section_cfg, packet)
            gen_mode = GenerationMode.TABLE

        # 3. LLM Mode
        elif mode_str == "llm":
            content = self.llm.generate(section_cfg, packet)
            gen_mode = GenerationMode.LLM

        # 4. Table + LLM Mode
        elif mode_str == "table_and_llm":
            table_part = render_table_section(section_cfg, packet)
            llm_narrative = self.llm.generate(section_cfg, packet)
            
            # Remove redundant title from LLM narrative if present
            lines = llm_narrative.split("\n")
            if lines and lines[0].startswith("## "):
                lines = lines[1:]
            narrative_text = "\n".join(lines).strip()

            content = f"{table_part}\n\n### Clinical Analysis and Interpretation\n\n{narrative_text}"
            gen_mode = GenerationMode.TABLE_AND_LLM

        else:
            raise ValueError(f"Unknown generation mode '{mode_str}' in section '{section_cfg.id}'.")

        return SectionDraft(
            section_id=section_cfg.id,
            title=section_cfg.title,
            order=section_cfg.order,
            generation_mode=gen_mode,
            markdown_content=content,
            evidence_ids_used=evidence_ids,
            model_name=self.llm.model_name if "llm" in mode_str else None,
            metadata={"generation_mode": mode_str, "items_count": len(packet.items)},
        )

    def generate_all(
        self,
        report_cfg: ReportConfig,
        packets: Dict[str, EvidencePacket],
    ) -> List[SectionDraft]:
        """Generate all report section drafts sorted in configured order."""
        drafts: List[SectionDraft] = []
        sorted_sections = sorted(report_cfg.sections, key=lambda s: s.order)

        for sec_cfg in sorted_sections:
            pkt = packets.get(sec_cfg.id)
            if not pkt:
                raise KeyError(f"Evidence packet missing for configured section '{sec_cfg.id}'.")
            draft = self.generate_section(sec_cfg, pkt)
            drafts.append(draft)

        return drafts
