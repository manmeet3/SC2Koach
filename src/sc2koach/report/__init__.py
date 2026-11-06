"""Report writer: Markdown + findings JSON from an AnalysisResult (design/DESIGN.md §8)."""

from sc2koach.report.markdown import render_markdown, write_outputs
from sc2koach.report.templates import finding_text

__all__ = ["finding_text", "render_markdown", "write_outputs"]
