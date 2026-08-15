"""Section generation engine supporting template, table, and LLM rendering modes."""

from genar.generation.dispatcher import SectionGenerator
from genar.generation.llm import LLMGenerator, build_llm_prompt
from genar.generation.tables import render_markdown_table, render_table_section
from genar.generation.templates import render_template_section

__all__ = [
    "SectionGenerator",
    "LLMGenerator",
    "build_llm_prompt",
    "render_template_section",
    "render_markdown_table",
    "render_table_section",
]
