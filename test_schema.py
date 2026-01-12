"""
Simple test: Just test schema induction with Google Gemini
This is the part that's failing with JSON parsing errors
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from structrag_mcp.storage import DuckDBManager
from structrag_mcp.ingestion import PDFParser, SemanticChunker
from structrag_mcp.structure.schema_inductor import SchemaInductor

def test_schema_induction(pdf_path: str):
    """Test just the schema induction part"""
    
    print("=" * 60)
    print("Schema Induction Test with Google Gemini")
    print("=" * 60)
    
    # Create temp database
    import tempfile
    db_file = tempfile.mktemp(suffix=".db")
    
    try:
        # Initialize
        print("\n📦 Initializing database...")
        db = DuckDBManager(db_file)
        
        # Parse PDF
        print(f"\n📄 Parsing {Path(pdf_path).name}...")
        parser = PDFParser()
        parsed = parser.parse(pdf_path)
        text = parsed.get('text', '') if isinstance(parsed, dict) else str(parsed)
        print(f"✅ Got {len(text)} characters")
        
        # Chunk
        print("\n✂️  Chunking text...")
        chunker = SemanticChunker(chunk_size=512, overlap=50)
        chunks = chunker.chunk_text(text)
        print(f"✅ Created {len(chunks)} chunks")
        
        # Store chunks  
        print("\n💾 Storing chunks...")
        chunk_records = []
        for i, chunk in enumerate(chunks[:10]):  # Only first 10 for speed
            chunk_records.append({
                "doc_id": "test-doc",
                "chunk_id": f"chunk-{i}",
                "chunk_index": i,
                "content": chunk,
                "tokens": len(chunk.split()),
                "metadata": {}
            })
        
        db.insert_chunks(chunk_records)
        print(f"✅ Stored {len(chunk_records)} chunks")
        
        # Test schema induction
        print("\n🔍 Running schema induction with Google Gemini...")
        print("   (This is where the JSON parsing error occurs)")
        
        inductor = SchemaInductor(db)
        
        try:
            result = inductor.induce_schema(
                entity_hints=["Company", "Financial", "Person"],
                max_samples=3,  # Small for speed
                min_confidence=0.6
            )
            
            print(f"\n✅ SUCCESS! Discovered {len(result.discovered_entities)} schemas:")
            for schema in result.discovered_entities:
                print(f"   - {schema.name} ({len(schema.attributes)} attributes)")
                for attr in schema.attributes[:3]:  # Show first 3
                    print(f"      • {attr.name}: {attr.data_type}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ FAILED: {str(e)}")
            print("\nThis means Google Gemini is returning invalid JSON.")
            print("The error handling needs to be improved.")
            import traceback
            traceback.print_exc()
            return False
    
    finally:
        # Cleanup
        if Path(db_file).exists():
            Path(db_file).unlink()


if __name__ == "__main__":
    # Get PDF path
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Find first PDF
        pdfs = list(Path("testdoc").glob("*.pdf")) if Path("testdoc").exists() else []
        if not pdfs:
            print("No PDF found. Usage: python test_schema.py <pdf_path>")
            sys.exit(1)
        pdf_path = str(pdfs[0])
    
    print(f"Testing with: {pdf_path}\n")
    success = test_schema_induction(pdf_path)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Test passed - schema induction works!")
        print("   Ready to use in Streamlit app")
    else:
        print("❌ Test failed - needs fixing before Streamlit")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
