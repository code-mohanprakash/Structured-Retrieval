"""
CSV Parser for StructRAG MCP
Reads CSV/TSV files using pandas
"""
from typing import Dict, List, Optional
from pathlib import Path
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class CSVParser:
    """Parse CSV/TSV files and extract structured data"""
    
    def __init__(self):
        self.supported_extensions = [".csv", ".tsv", ".txt"]
    
    def parse(self, file_path: str, delimiter: Optional[str] = None) -> Dict[str, any]:
        """
        Parse a CSV/TSV file
        
        Args:
            file_path: Path to CSV file
            delimiter: Column delimiter (auto-detected if None)
            
        Returns:
            Dict containing:
                - text: Text representation of data
                - data: List of row dictionaries
                - columns: List of column names
                - row_count: Number of data rows
                - metadata: File metadata
        """
        try:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"CSV file not found: {file_path}")
            
            # Auto-detect delimiter if not provided
            if delimiter is None:
                if path.suffix.lower() == ".tsv":
                    delimiter = "\t"
                else:
                    delimiter = ","
            
            # Read CSV
            df = pd.read_csv(file_path, delimiter=delimiter, encoding="utf-8")
            
            # Convert to records
            records = df.to_dict("records")
            
            # Create text representation
            text_lines = [
                f"CSV Data: {path.name}",
                f"Columns: {', '.join(df.columns)}",
                f"Rows: {len(df)}",
                "",
                "Data:"
            ]
            
            # Add sample rows to text (first 10)
            sample_size = min(10, len(df))
            for idx, row in enumerate(records[:sample_size]):
                text_lines.append(f"Row {idx + 1}: {row}")
            
            if len(df) > sample_size:
                text_lines.append(f"... ({len(df) - sample_size} more rows)")
            
            return {
                "text": "\n".join(text_lines),
                "metadata": {
                    "file_name": path.name,
                    "file_size": path.stat().st_size,
                    "delimiter": delimiter,
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "data": records,
                    "columns": list(df.columns),
                    "row_count": len(df),
                    "column_count": len(df.columns)
                }
            }
            
        except Exception as e:
            logger.error(f"Error parsing CSV {file_path}: {e}")
            raise ValueError(f"Failed to parse CSV: {str(e)}")
    
    def is_supported(self, file_path: str) -> bool:
        """Check if file extension is supported"""
        return Path(file_path).suffix.lower() in self.supported_extensions
