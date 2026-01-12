"""
PDF Parser for StructRAG MCP
Extracts text from PDF files with metadata preservation
"""
from typing import Dict, List, Optional
from pathlib import Path
import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class PDFParser:
    """Parse PDF documents and extract text with metadata"""
    
    def __init__(self):
        self.supported_extensions = [".pdf"]
    
    def parse(self, file_path: str) -> Dict[str, any]:
        """
        Parse a PDF file and extract text with metadata
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dict containing:
                - text: Full extracted text
                - pages: List of page texts
                - metadata: PDF metadata (author, title, etc.)
                - page_count: Number of pages
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"PDF file not found: {file_path}")
            
            reader = PdfReader(str(path))
            
            # Extract metadata
            metadata = {}
            if reader.metadata:
                metadata = {
                    "author": reader.metadata.get("/Author", ""),
                    "title": reader.metadata.get("/Title", ""),
                    "subject": reader.metadata.get("/Subject", ""),
                    "creator": reader.metadata.get("/Creator", ""),
                    "producer": reader.metadata.get("/Producer", ""),
                    "creation_date": str(reader.metadata.get("/CreationDate", "")),
                }
            
            # Extract text from all pages
            pages = []
            full_text = []
            
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        pages.append({
                            "page_number": page_num,
                            "text": page_text.strip()
                        })
                        full_text.append(page_text)
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num}: {e}")
                    pages.append({
                        "page_number": page_num,
                        "text": "",
                        "error": str(e)
                    })
            
            return {
                "text": "\n\n".join(full_text),
                "pages": pages,
                "metadata": metadata,
                "page_count": len(reader.pages),
                "file_size": path.stat().st_size,
                "file_name": path.name
            }
            
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {e}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file extension is supported"""
        return Path(file_path).suffix.lower() in self.supported_extensions
