"""
PDF Processor - Extract and chunk PDF content for RLM analysis

Handles PDF parsing, text extraction, and intelligent chunking
for Recursive Language Model processing.
"""

import re
import os
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PDFChunk:
    """A chunk of PDF content"""
    content: str
    start_page: int
    end_page: int
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class PDFDocument:
    """Parsed PDF document with metadata"""
    title: str
    author: str = ""
    content: str = ""
    pages: List[str] = None
    total_pages: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.pages is None:
            self.pages = []
        if self.metadata is None:
            self.metadata = {}


class PDFProcessor:
    """
    PDF processing utilities for RLM skill.

    Extracts text from PDFs and prepares them for recursive analysis.
    """

    def __init__(self, chunk_size: int = 10_000, overlap: int = 500):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def extract_from_file(self, pdf_path: str) -> PDFDocument:
        """
        Extract text content from PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            PDFDocument with extracted content
        """
        pdf_path = Path(pdf_path)

        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Try different PDF extraction methods
        content = self._extract_with_pymupdf(pdf_path)
        if not content:
            content = self._extract_with_pypdf2(pdf_path)
        if not content:
            content = self._extract_basic(pdf_path)

        return PDFDocument(
            title=pdf_path.stem,
            content=content,
            total_pages=len(content.split('\f')) if content else 0,
            metadata={"source": str(pdf_path)}
        )

    def extract_from_url(self, url: str) -> PDFDocument:
        """
        Extract text content from PDF at URL.

        Args:
            url: URL to PDF file

        Returns:
            PDFDocument with extracted content
        """
        import requests

        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Save to temp file
        temp_path = Path("temp_pdf.pdf")
        temp_path.write_bytes(response.content)

        try:
            return self.extract_from_file(str(temp_path))
        finally:
            temp_path.unlink(missing_ok=True)

    def chunk_document(self, document: PDFDocument) -> List[PDFChunk]:
        """
        Split document into intelligent chunks for RLM processing.

        Args:
            document: PDFDocument to chunk

        Returns:
            List of PDFChunk objects
        """
        chunks = []

        # Try to chunk by sections first
        section_chunks = self._chunk_by_sections(document)
        if len(section_chunks) > 1:
            return section_chunks

        # Fall back to size-based chunking
        return self._chunk_by_size(document)

    def _extract_with_pymupdf(self, pdf_path: Path) -> str:
        """Extract text using PyMuPDF (fitz)"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return ""

        try:
            doc = fitz.open(str(pdf_path))
            text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            doc.close()
            return "\n\n".join(text_parts)

        except Exception as e:
            print(f"[PDF] PyMuPDF extraction failed: {e}")
            return ""

    def _extract_with_pypdf2(self, pdf_path: Path) -> str:
        """Extract text using PyPDF2"""
        try:
            import PyPDF2
        except ImportError:
            return ""

        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text_parts = []

                for page_num, page in enumerate(reader.pages):
                    text = page.extract_text()
                    if text.strip():
                        text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

                return "\n\n".join(text_parts)

        except Exception as e:
            print(f"[PDF] PyPDF2 extraction failed: {e}")
            return ""

    def _extract_basic(self, pdf_path: Path) -> str:
        """Basic PDF text extraction fallback"""
        # This is a placeholder - in real implementation would use
        # a more robust fallback method
        return f"[Could not extract text from {pdf_path.name}. Please install PyMuPDF or PyPDF2.]"

    def _chunk_by_sections(self, document: PDFDocument) -> List[PDFChunk]:
        """Chunk document by detected sections (headers, etc.)"""
        chunks = []
        content = document.content

        # Common section header patterns
        section_patterns = [
            r'^\n?(#{1,3}\s+.+?)\n',  # Markdown headers
            r'^\n?([A-Z][A-Z\s]{5,})\n',  # ALL CAPS headers
            r'^\n?(\d+\.\s+.+?)\n',  # Numbered sections
            r'^\n?([IVX]+\.\s+.+?)\n',  # Roman numeral sections
        ]

        # Find all section boundaries
        boundaries = [0]
        for pattern in section_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                boundaries.append(match.start())

        boundaries = sorted(set(boundaries))
        boundaries.append(len(content))

        # Create chunks from boundaries
        if len(boundaries) > 2:  # Only use if we found meaningful sections
            for i in range(len(boundaries) - 1):
                start = boundaries[i]
                end = boundaries[i + 1]
                chunk_content = content[start:end].strip()

                if len(chunk_content) > 100:  # Skip tiny chunks
                    chunks.append(PDFChunk(
                        content=chunk_content,
                        start_page=i + 1,
                        end_page=i + 1,
                        metadata={"method": "section"}
                    ))

        return chunks

    def _chunk_by_size(self, document: PDFDocument) -> List[PDFChunk]:
        """Chunk document by size with overlap"""
        chunks = []
        content = document.content

        start = 0
        chunk_num = 0

        while start < len(content):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(content):
                # Look for sentence end near chunk_size
                sentence_end = content.rfind('.', start, end + 200)
                if sentence_end > start + self.chunk_size // 2:
                    end = sentence_end + 1
                else:
                    # Try paragraph break
                    para_end = content.rfind('\n\n', start, end + 200)
                    if para_end > start + self.chunk_size // 2:
                        end = para_end + 2

            chunk_content = content[start:end].strip()

            if len(chunk_content) > 100:
                chunks.append(PDFChunk(
                    content=chunk_content,
                    start_page=chunk_num + 1,
                    end_page=chunk_num + 1,
                    metadata={"method": "size", "char_start": start, "char_end": end}
                ))
                chunk_num += 1

            start = end - self.overlap

        return chunks

    def get_structure_info(self, document: PDFDocument) -> Dict[str, Any]:
        """
        Analyze document structure for intelligent processing.

        Args:
            document: PDFDocument to analyze

        Returns:
            Dictionary with structure information
        """
        content = document.content

        # Count pages (approximate by form feeds)
        pages = content.split('\f')
        page_count = len(pages)

        # Detect sections
        section_count = len(re.findall(r'^#{1,3}\s+', content, re.MULTILINE))

        # Detect tables
        table_count = len(re.findall(r'\|.+\|', content))

        # Detect code blocks
        code_count = len(re.findall(r'```[\s\S]*?```', content))

        # Get average words per page
        words = content.split()
        avg_words_per_page = len(words) / max(page_count, 1)

        return {
            "total_pages": page_count,
            "total_words": len(words),
            "total_chars": len(content),
            "sections_detected": section_count,
            "tables_detected": table_count,
            "code_blocks_detected": code_count,
            "avg_words_per_page": int(avg_words_per_page),
            "recommended_chunking": "section" if section_count > 5 else "size"
        }

    def create_context_for_rlm(self, document: PDFDocument) -> str:
        """
        Create formatted context string for RLM processing.

        Args:
            document: PDFDocument to format

        Returns:
            Formatted context string
        """
        structure = self.get_structure_info(document)

        context = f"""# PDF Document: {document.title}

## Document Structure
- Total pages: {structure['total_pages']}
- Total words: {structure['total_words']:,}
- Total characters: {structure['total_chars']:,}
- Sections detected: {structure['sections_detected']}
- Tables detected: {structure['tables_detected']}
- Code blocks: {structure['code_blocks_detected']}

## Full Content
{document.content}
"""

        return context


def create_pdf_processor(**kwargs) -> PDFProcessor:
    """Factory function to create PDF processor"""
    return PDFProcessor(**kwargs)
