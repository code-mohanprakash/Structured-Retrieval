"""Tests for ingestion parsers"""

import pytest
from pathlib import Path
import tempfile

from structrag_mcp.ingestion import TextParser, CSVParser, SemanticChunker


def test_text_parser():
    """Test text file parsing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test document.\nWith multiple lines.")
        temp_path = f.name
    
    try:
        parser = TextParser()
        result = parser.parse(temp_path)
        
        assert "text" in result
        assert "This is a test document" in result["text"]
        assert "metadata" in result
    finally:
        Path(temp_path).unlink()


def test_csv_parser():
    """Test CSV parsing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write("name,age,city\nAlice,30,NYC\nBob,25,SF")
        temp_path = f.name
    
    try:
        parser = CSVParser()
        result = parser.parse(temp_path)
        
        assert "text" in result
        assert "Alice" in result["text"]
        assert "metadata" in result
        assert result["metadata"]["row_count"] == 2
    finally:
        Path(temp_path).unlink()


def test_chunker_basic():
    """Test basic text chunking"""
    chunker = SemanticChunker(chunk_size=50, overlap=10)
    
    text = "This is a test sentence. " * 20
    chunks = chunker.chunk(text, {})
    
    assert len(chunks) > 1
    assert all(chunk["token_count"] <= 50 for chunk in chunks)
    assert all("chunk_index" in chunk for chunk in chunks)


def test_chunker_small_text():
    """Test chunking with text smaller than max size"""
    chunker = SemanticChunker(chunk_size=1000, overlap=50)
    
    text = "Short text"
    chunks = chunker.chunk(text, {})
    
    assert len(chunks) == 1
    assert chunks[0]["text"] == text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
