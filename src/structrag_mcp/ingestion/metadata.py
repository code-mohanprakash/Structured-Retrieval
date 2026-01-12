"""
Metadata Extraction for StructRAG MCP
Extracts and normalizes metadata from documents
"""
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extract and normalize metadata from various document sources"""
    
    def extract_file_metadata(self, file_path: str) -> Dict[str, any]:
        """
        Extract basic file system metadata
        
        Args:
            file_path: Path to file
            
        Returns:
            Dict with file metadata
        """
        try:
            path = Path(file_path)
            stat = path.stat()
            
            return {
                "file_name": path.name,
                "file_path": str(path.absolute()),
                "file_size": stat.st_size,
                "file_extension": path.suffix.lower(),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        except Exception as e:
            logger.error(f"Error extracting file metadata from {file_path}: {e}")
            return {}
    
    def normalize_metadata(
        self, 
        file_metadata: Dict,
        document_metadata: Dict = None,
        custom_metadata: Dict = None
    ) -> Dict[str, any]:
        """
        Combine and normalize metadata from multiple sources
        
        Args:
            file_metadata: File system metadata
            document_metadata: Document-specific metadata (PDF, etc.)
            custom_metadata: User-provided metadata
            
        Returns:
            Normalized metadata dictionary
        """
        normalized = {
            "source_type": self._detect_source_type(file_metadata.get("file_extension", "")),
            "ingested_at": datetime.now().isoformat(),
        }
        
        # Merge all metadata sources
        if file_metadata:
            normalized.update(file_metadata)
        
        if document_metadata:
            # Normalize document metadata keys
            normalized["doc_metadata"] = self._normalize_doc_metadata(document_metadata)
        
        if custom_metadata:
            normalized["custom"] = custom_metadata
        
        return normalized
    
    def _detect_source_type(self, extension: str) -> str:
        """Detect source type from file extension"""
        extension = extension.lower().lstrip(".")
        
        source_map = {
            "pdf": "pdf",
            "csv": "csv",
            "tsv": "csv",
            "txt": "text",
            "md": "markdown",
            "markdown": "markdown",
            "json": "json",
        }
        
        return source_map.get(extension, "unknown")
    
    def _normalize_doc_metadata(self, doc_meta: Dict) -> Dict[str, any]:
        """Normalize document-specific metadata"""
        normalized = {}
        
        # Common fields
        if "author" in doc_meta:
            normalized["author"] = doc_meta["author"]
        if "title" in doc_meta:
            normalized["title"] = doc_meta["title"]
        if "subject" in doc_meta:
            normalized["subject"] = doc_meta["subject"]
        if "creation_date" in doc_meta:
            normalized["created"] = doc_meta["creation_date"]
        
        # Keep original
        normalized["raw"] = doc_meta
        
        return normalized
    
    def extract_entities_from_text(self, text: str) -> Dict[str, any]:
        """
        Extract basic entities from text (simple version)
        TODO: Enhance with NER models in Phase 2
        
        Args:
            text: Document text
            
        Returns:
            Dict with extracted entities
        """
        import re
        
        entities = {}
        
        # Extract emails
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if emails:
            entities["emails"] = list(set(emails))[:10]  # Limit to 10
        
        # Extract dates (simple patterns)
        dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}/\d{4}\b', text)
        if dates:
            entities["dates"] = list(set(dates))[:10]
        
        # Extract dollar amounts
        amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?', text)
        if amounts:
            entities["amounts"] = list(set(amounts))[:10]
        
        return entities
