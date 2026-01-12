"""
Text Parser for StructRAG MCP
Handles plain text, markdown, and JSON files
"""
from typing import Dict
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)


class TextParser:
    """Parse plain text, markdown, and JSON files"""
    
    def __init__(self):
        self.supported_extensions = [".txt", ".md", ".markdown", ".json"]
    
    def parse(self, file_path: str) -> Dict[str, any]:
        """
        Parse a text file
        
        Args:
            file_path: Path to text file
            
        Returns:
            Dict containing:
                - text: Extracted text content
                - metadata: File metadata
                - format: File format (txt, md, json)
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Text file not found: {file_path}")
            
            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Determine format
            file_format = path.suffix.lower().lstrip(".")
            if file_format == "markdown":
                file_format = "md"
            
            # Special handling for JSON
            parsed_data = None
            if file_format == "json":
                try:
                    parsed_data = json.loads(content)
                    # Create readable text representation
                    content = json.dumps(parsed_data, indent=2)
                except json.JSONDecodeError as e:
                    logger.warning(f"Invalid JSON in {file_path}: {e}")
            
            return {
                "text": content,
                "metadata": {
                    "file_name": path.name,
                    "file_size": path.stat().st_size,
                    "format": file_format,
                    "line_count": content.count("\n") + 1,
                    "char_count": len(content)
                },
                "parsed_data": parsed_data  # Only set for JSON
            }
            
        except Exception as e:
            logger.error(f"Error parsing text file {file_path}: {e}")
            raise ValueError(f"Failed to parse text file: {str(e)}")
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file extension is supported"""
        return Path(file_path).suffix.lower() in self.supported_extensions
