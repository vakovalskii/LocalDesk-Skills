"""
RLM PDF Reader - Claude Code Skill

Recursive Language Model implementation for reading large PDF documents.
Based on arXiv:2512.24601 - https://arxiv.org/pdf/2512.24601
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Add skill directory to path
skill_dir = Path(__file__).parent
if str(skill_dir) not in sys.path:
    sys.path.insert(0, str(skill_dir))

from rlm_engine import create_rlm_engine
from pdf_processor import create_pdf_processor


class RLMPDFReader:
    """Main skill handler for RLM PDF Reader"""

    def __init__(self):
        self.rlm_engine = None
        self.pdf_processor = None

    def initialize(self):
        """Initialize RLM engine and PDF processor"""
        self.rlm_engine = create_rlm_engine(
            max_iterations=10,
            verbose=False
        )
        self.pdf_processor = create_pdf_processor(
            chunk_size=10_000,
            overlap=500
        )

    def process_pdf(
        self,
        pdf_path: str,
        query: str,
        cli_tool=None
    ) -> Optional[str]:
        """
        Process a PDF document using RLM.

        Args:
            pdf_path: Path or URL to PDF file
            query: Question or task for the document
            cli_tool: Claude Code CLI tool function

        Returns:
            Answer to the query, or None if failed
        """
        if cli_tool is None:
            return "Error: cli_tool is required for RLM operation"

        try:
            # Initialize if needed
            if self.rlm_engine is None:
                self.initialize()

            # Extract PDF content
            if pdf_path.startswith('http://') or pdf_path.startswith('https://'):
                document = self.pdf_processor.extract_from_url(pdf_path)
            else:
                document = self.pdf_processor.extract_from_file(pdf_path)

            # Create context for RLM
            context = self.pdf_processor.create_context_for_rlm(document)

            # Run RLM analysis
            answer = self.rlm_engine.completion(
                context=context,
                query=query,
                cli_tool=cli_tool
            )

            # Add statistics
            stats = self.rlm_engine.get_stats()

            if answer:
                result = f"""# RLM Analysis Result

{answer}

---
## RLM Statistics
- Iterations: {stats['iterations']}
- Root LLM calls: {stats['root_calls']}
- Sub-LLM calls: {stats['sub_calls']}
- Total LLM calls: {stats['total_calls']}
- Root tokens: {stats['root_tokens']:,}
- Sub-tokens: {stats['sub_tokens']:,}
- Total tokens: {stats['total_tokens']:,}
"""
            else:
                result = "RLM analysis did not converge within max iterations."

            return result

        except Exception as e:
            return f"Error processing PDF: {str(e)}"

    def analyze_structure(self, pdf_path: str) -> str:
        """
        Analyze PDF structure without running full RLM.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Structure analysis report
        """
        try:
            if self.pdf_processor is None:
                self.initialize()

            document = self.pdf_processor.extract_from_file(pdf_path)
            structure = self.pdf_processor.get_structure_info(document)

            report = f"""# PDF Structure Analysis

## Document: {document.title}

### Basic Statistics
- Total pages: {structure['total_pages']}
- Total words: {structure['total_words']:,}
- Total characters: {structure['total_chars']:,}

### Content Detection
- Sections detected: {structure['sections_detected']}
- Tables detected: {structure['tables_detected']}
- Code blocks detected: {structure['code_blocks_detected']}

### Processing Recommendations
- Average words per page: {structure['avg_words_per_page']:,}
- Recommended chunking method: {structure['recommended_chunking']}

### Content Preview
{document.content[:1000]}...
"""
            return report

        except Exception as e:
            return f"Error analyzing PDF: {str(e)}"


# Global skill instance
_skill_instance = None


def get_skill() -> RLMPDFReader:
    """Get or create skill instance"""
    global _skill_instance
    if _skill_instance is None:
        _skill_instance = RLMPDFReader()
    return _skill_instance


# Skill entry point
def skill_main(pdf_path: str, query: str, cli_tool=None) -> str:
    """
    Main entry point for Claude Code skill invocation.

    Usage:
        /rlm-pdf <path_to_pdf> "<your query>"

    Examples:
        /rlm-pdf document.pdf "What are the main findings?"
        /rlm-pdf report.pdf "Summarize the methodology section"
    """
    skill = get_skill()
    return skill.process_pdf(pdf_path, query, cli_tool)


def skill_analyze(pdf_path: str) -> str:
    """
    Analyze PDF structure.

    Usage:
        /rlm-analyze <path_to_pdf>
    """
    skill = get_skill()
    return skill.analyze_structure(pdf_path)


# Export for Claude Code
__all__ = [
    'skill_main',
    'skill_analyze',
    'RLMPDFReader',
    'get_skill'
]
