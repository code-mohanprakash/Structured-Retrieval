"""
Basic integration tests for StructRAG MCP

These tests verify the core workflow:
1. Document ingestion
2. Schema induction
3. Entity extraction
4. Query execution
"""

import pytest
import os
import tempfile
from pathlib import Path

from structrag_mcp.storage import DuckDBManager, ProvenanceTracker
from structrag_mcp.ingestion import PDFParser, CSVParser, TextParser, SemanticChunker
from structrag_mcp.structure import SchemaInductor, EntityExtractor
from structrag_mcp.structure.models import EntitySchema, FieldDefinition
from structrag_mcp.query import QueryEngine


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    # Get a temporary path but don't create the file yet
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)  # Close the file descriptor
    os.unlink(db_path)  # Remove the empty file (DuckDB will create it)
    
    db = DuckDBManager(db_path)
    yield db
    
    db.close()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def sample_text_file(tmp_path):
    """Create sample text file for testing"""
    content = """
    SALES CALL TRANSCRIPT - Deal #001
    
    Company: Acme Corp
    Contact: John Smith (CTO)
    Deal Value: $50,000
    Status: Closed-Won
    Close Date: 2024-01-15
    
    Notes: Customer needs enterprise software license for 100 users.
    Strong interest in annual support package.
    """
    
    file_path = tmp_path / "deal_001.txt"
    file_path.write_text(content)
    return str(file_path)


def test_text_parser(sample_text_file):
    """Test text file parsing"""
    parser = TextParser()
    result = parser.parse(sample_text_file)
    
    assert "text" in result
    assert "Acme Corp" in result["text"]
    assert "50,000" in result["text"]


def test_chunker():
    """Test text chunking"""
    chunker = SemanticChunker(chunk_size=100, overlap=20)
    
    text = "This is a test sentence. " * 50  # Create long text
    chunks = chunker.chunk(text, metadata={"source": "test"})
    
    assert len(chunks) > 1
    assert all("text" in chunk for chunk in chunks)
    assert all("chunk_index" in chunk for chunk in chunks)
    assert all("token_count" in chunk for chunk in chunks)


def test_duckdb_manager(temp_db):
    """Test DuckDB operations"""
    # Check core tables exist
    tables = temp_db.list_tables()
    assert "documents" in tables
    assert "chunks" in tables
    assert "query_provenance" in tables
    assert "schema_registry" in tables
    
    # Test document insertion
    temp_db.insert_document(
        doc_id="test_doc_1",
        filename="test.txt",
        file_path="/tmp/test.txt",
        file_type=".txt",
        metadata={"test": True}
    )
    
    doc_count = temp_db.get_document_count()
    assert doc_count == 1


def test_provenance_tracker(temp_db):
    """Test provenance tracking"""
    provenance = ProvenanceTracker(temp_db)
    
    # Test ID generation
    doc_id = provenance.generate_doc_id("file.txt", "/path/to/file.txt")
    assert doc_id.startswith("doc_") or len(doc_id) == 16  # MD5 prefix is 16 chars
    
    query_id = provenance.generate_query_id("test query")
    assert len(query_id) == 16  # MD5 hash prefix
    
    chunk_id = provenance.generate_chunk_id("doc_123", 0)
    assert chunk_id == "doc_123_chunk_0"


def test_schema_validation():
    """Test Pydantic schema models"""
    # Create valid schema
    schema = EntitySchema(
        name="Deal",
        attributes=[
            FieldDefinition(
                name="deal_id",
                type="TEXT",
                confidence=1.0,
                is_primary_key=True
            ),
            FieldDefinition(
                name="deal_value",
                type="REAL",
                confidence=0.9
            )
        ]
    )
    
    assert schema.name == "Deal"
    assert len(schema.attributes) == 2
    
    # Test DDL generation
    ddl = schema.to_duckdb_ddl()
    assert "CREATE TABLE" in ddl
    assert "deal_id TEXT PRIMARY KEY" in ddl


def test_end_to_end_workflow(temp_db, sample_text_file):
    """Test complete workflow from ingestion to query"""
    
    # 1. Ingest document
    parser = TextParser()
    parsed = parser.parse(sample_text_file)
    
    provenance = ProvenanceTracker(temp_db)
    doc_id = provenance.generate_doc_id(os.path.basename(sample_text_file), sample_text_file)
    
    temp_db.insert_document(
        doc_id=doc_id,
        filename="deal_001.txt",
        file_path=sample_text_file,
        file_type=".txt",
        metadata={}
    )
    
    # 2. Chunk text
    chunker = SemanticChunker()
    chunks = chunker.chunk(parsed["text"], {})
    
    for chunk in chunks:
        chunk_id = provenance.generate_chunk_id(doc_id, chunk["chunk_index"])
        temp_db.insert_chunks([{
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "chunk_index": chunk["chunk_index"],
            "text": chunk["text"],
            "token_count": chunk["token_count"],
            "metadata": {}
        }])
    
    # 3. Verify storage
    doc_count = temp_db.get_document_count()
    chunk_count = temp_db.get_chunk_count()
    
    assert doc_count == 1
    assert chunk_count == len(chunks)
    
    # 4. Create simple schema manually (skip LLM for unit test)
    schema = EntitySchema(
        name="Deal",
        table_name="deal",
        attributes=[
            FieldDefinition(name="deal_id", type="TEXT", confidence=1.0, is_primary_key=True),
            FieldDefinition(name="company_name", type="TEXT", confidence=0.9),
            FieldDefinition(name="deal_value", type="REAL", confidence=0.9)
        ]
    )
    
    # Create table
    ddl = schema.to_duckdb_ddl()
    temp_db.execute_query(ddl)
    
    # Verify table created
    tables = temp_db.list_tables()
    assert "deal" in tables
    
    # 5. Insert test entity
    temp_db.execute_query(
        "INSERT INTO deal (deal_id, company_name, deal_value) VALUES (?, ?, ?)",
        params=["deal_001", "Acme Corp", 50000.0]
    )
    
    # 6. Query data
    results = temp_db.execute_query("SELECT * FROM deal WHERE company_name = ?", params=["Acme Corp"])
    
    assert len(results) == 1
    assert results[0]["deal_value"] == 50000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
