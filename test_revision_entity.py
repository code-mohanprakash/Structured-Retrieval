#!/usr/bin/env python
import sys
import os
from pathlib import Path

# Set up path
sys.path.insert(0, str(Path('/Users/mohanjeyasankar/Desktop/postition/src')))

# Load environment
from dotenv import load_dotenv
load_dotenv('/Users/mohanjeyasankar/Desktop/postition/.env')

from structrag_mcp.storage import DuckDBManager
from structrag_mcp.ingestion import PDFParser, SemanticChunker, MetadataExtractor
from structrag_mcp.structure import SchemaInductor

# Initialize components
db = DuckDBManager('./data/test_structrag.db')
pdf_parser = PDFParser()
chunker = SemanticChunker()
metadata_extractor = MetadataExtractor()

# Ingest PDF
pdf_path = '/Users/mohanjeyasankar/Desktop/postition/testdoc/occidental_ars.pdf'
print(f"🔄 Ingesting: {pdf_path}\n")

try:
    parsed = pdf_parser.parse(pdf_path)
    print(f"✓ Parsed PDF, content length: {len(parsed['text'])} chars")
    
    # Extract metadata
    file_metadata = metadata_extractor.extract_file_metadata(pdf_path)
    
    # Insert document
    doc_id = f"doc_{Path(pdf_path).stem}"
    db.insert_document(
        doc_id=doc_id,
        filename=Path(pdf_path).name,
        file_path=pdf_path,
        file_type=".pdf",
        metadata=file_metadata
    )
    print(f"✓ Document stored with ID: {doc_id}")
    
    # Chunk the text
    chunks = chunker.chunk(parsed['text'], file_metadata)
    print(f"✓ Created {len(chunks)} chunks")
    
    # Insert chunks
    for i, chunk in enumerate(chunks):
        chunk_id = f"{doc_id}_chunk_{chunk['chunk_index']}"
        db.insert_chunks([{
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "chunk_index": chunk["chunk_index"],
            "text": chunk["text"],
            "token_count": chunk["token_count"],
            "metadata": chunk.get("metadata", {})
        }])
    
    print(f"✓ Stored all chunks in database\n")
    
    # Now build structure for "Revisions of previous estimates"
    print("="*60)
    print("🏗️  Building structure for entity: 'Revisions of previous estimates'")
    print("="*60)
    inductor = SchemaInductor(db)
    
    result = inductor.induce_schema_iterative(
        entity_hints=["Revisions of previous estimates"],
        num_iterations=2,  # Reduced for quick test
        num_documents=3,   # Reduced for quick test
        num_questions=3,   # Reduced for quick test
        min_confidence=0.5
    )
    
    print(f"\n✓ Schema induction complete!")
    print(f"✓ Entities discovered: {len(result.entities)}")
    print(f"✓ Model: {result.llm_model}")
    print(f"✓ Tokens used: {result.llm_tokens_used:,}\n")
    
    for entity in result.entities:
        print(f"📊 Entity: {entity.name}")
        print(f"   Table: {entity.table_name}")
        print(f"   Attributes: {len(entity.attributes)}")
        for attr in entity.attributes:
            pk = " 🔑" if attr.is_primary_key else ""
            print(f"     • {attr.name} ({attr.type}){pk}")
            if attr.examples:
                print(f"       → Examples: {attr.examples[:2]}")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
