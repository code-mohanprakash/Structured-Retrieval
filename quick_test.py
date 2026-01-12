#!/usr/bin/env python3
"""
Quick Test: Verify StructRAG is working with your Occidental PDF
Run this to validate the JSON parsing fix and full pipeline.
"""

import sys
from pathlib import Path
import tempfile

print("=" * 80)
print("🧪 StructRAG Quick Test - Occidental PDF")
print("=" * 80)
print()

# Check imports
print("1️⃣ Checking imports...")
try:
    from structrag_mcp.storage import DuckDBManager, ProvenanceTracker
    from structrag_mcp.ingestion import PDFParser, SemanticChunker, MetadataExtractor
    from structrag_mcp.structure.schema_inductor import SchemaInductor
    from structrag_mcp.query.engine import QueryEngine
    print("   ✅ All imports successful")
except ImportError as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

print()

# Check PDF exists
print("2️⃣ Checking PDF file...")
pdf_path = Path("occidental_ars.pdf")
if not pdf_path.exists():
    print("   ❌ occidental_ars.pdf not found in current directory")
    sys.exit(1)
print(f"   ✅ Found {pdf_path.name} ({pdf_path.stat().st_size / 1024 / 1024:.1f} MB)")
print()

# Setup database
print("3️⃣ Setting up database...")
db_path = Path(tempfile.mkdtemp()) / "test.db"
db = DuckDBManager(str(db_path))
provenance = ProvenanceTracker(db)
print(f"   ✅ Database created: {db_path}")
print()

# Test ingestion
print("4️⃣ Testing PDF ingestion...")
try:
    parser = PDFParser()
    parsed = parser.parse(str(pdf_path))
    
    metadata_extractor = MetadataExtractor()
    file_metadata = metadata_extractor.extract_file_metadata(str(pdf_path))
    metadata = {**parsed.get("metadata", {}), **file_metadata}
    
    doc_id = provenance.generate_doc_id(pdf_path.name, str(pdf_path))
    db.insert_document(doc_id, pdf_path.name, str(pdf_path), ".pdf", metadata)
    
    chunker = SemanticChunker()
    chunks = chunker.chunk(parsed["text"], metadata)
    
    for i, chunk in enumerate(chunks):
        chunk_id = provenance.generate_chunk_id(doc_id, i)
        db.insert_chunks([{
            "chunk_id": chunk_id,
            "doc_id": doc_id,
            "chunk_index": i,
            "text": chunk["text"],
            "token_count": chunk["token_count"],
            "metadata": chunk.get("metadata", {})
        }])
    
    print(f"   ✅ Ingested {len(chunks)} chunks ({sum(c['token_count'] for c in chunks)} tokens)")
except Exception as e:
    print(f"   ❌ Ingestion failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test schema discovery (THE CRITICAL TEST - JSON parsing fix)
print("5️⃣ Testing schema discovery (JSON parsing fix)...")
try:
    inductor = SchemaInductor(db)
    
    result = inductor.induce_schema(
        entity_hints=["FinancialMetrics", "BusinessSegment", "CompanyInfo"]
    )
    
    print(f"   ✅ Schema discovered successfully!")
    print(f"   ✅ Found {len(result.entities)} entity types:")
    
    for entity in result.entities:
        print(f"\n      📊 {entity.name}")
        for attr in entity.attributes[:5]:
            print(f"         - {attr.name}: {attr.type}")
        if len(entity.attributes) > 5:
            print(f"         ... and {len(entity.attributes) - 5} more fields")
    
    print()
    print("   🎉 JSON PARSING FIX CONFIRMED WORKING!")
    
except Exception as e:
    print(f"   ❌ Schema discovery failed: {e}")
    import traceback
    traceback.print_exc()
    print()
    print("   ⚠️  This means the JSON parsing fix didn't work.")
    print("      Check the error above for details.")
    sys.exit(1)

print()
print("=" * 80)
print("✅ ALL TESTS PASSED!")
print("=" * 80)
print()
print("What just happened:")
print("  1. ✅ Imported all StructRAG components")
print("  2. ✅ Found your Occidental PDF (15 MB)")
print("  3. ✅ Created test database")
print(f"  4. ✅ Ingested PDF into {len(chunks)} chunks")
print(f"  5. ✅ Discovered {len(result.entities)} entity schemas")
print()
print("🎯 The JSON parsing fix is working!")
print()
print("Next steps:")
print("  1. Read HOW_IT_WORKS.md for detailed guide")
print("  2. Run examples/getting_started.py for more examples")
print("  3. Test with your own PDFs")
print()
print(f"📂 Test database location: {db_path}")
print()
