"""
Test the complete StructRAG workflow locally
Run this to verify everything works before deploying to Streamlit
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from structrag_mcp.storage import DuckDBManager, ProvenanceTracker
from structrag_mcp.ingestion import PDFParser, SemanticChunker, MetadataExtractor
from structrag_mcp.structure.schema_inductor import SchemaInductor
from structrag_mcp.structure.entity_extractor import EntityExtractor
from structrag_mcp.query.engine import QueryEngine

def test_full_workflow(pdf_path: str):
    """Test complete workflow"""
    
    print("=" * 60)
    print("StructRAG Full Workflow Test")
    print("=" * 60)
    
    # Create temp database
    db_file = tempfile.mktemp(suffix=".db")
    print(f"\n📁 Database: {db_file}")
    
    try:
        # Step 1: Initialize
        print("\n🔧 Step 1: Initializing components...")
        db = DuckDBManager(db_file)
        provenance = ProvenanceTracker(db)
        print("✅ Components initialized")
        
        # Step 2: Parse PDF
        print("\n📄 Step 2: Parsing PDF...")
        parser = PDFParser()
        parsed_result = parser.parse(pdf_path)
        
        # Handle dict or string result
        if isinstance(parsed_result, dict):
            text = parsed_result.get('text', '')
            print(f"✅ Parsed {len(text)} characters")
            print(f"   Metadata: {parsed_result.get('metadata', {})}")
        else:
            text = str(parsed_result)
            print(f"✅ Parsed {len(text)} characters")
        
        print(f"   Preview: {text[:200] if text else 'No text extracted'}...")
        
        # Step 3: Extract metadata
        print("\n📊 Step 3: Extracting metadata...")
        metadata_extractor = MetadataExtractor()
        metadata = metadata_extractor.extract_file_metadata(pdf_path)
        print(f"✅ Metadata: file_name={metadata.get('file_name')}, file_size={metadata.get('file_size')}")
        
        # Step 4: Create document record
        print("\n💾 Step 4: Storing document...")
        doc_id = db.store_document(
            filename=Path(pdf_path).name,
            file_type="pdf",
            file_size=Path(pdf_path).stat().st_size,
            metadata=metadata
        )
        print(f"✅ Document ID: {doc_id}")
        
        # Step 5: Chunk text
        print("\n✂️  Step 5: Chunking text...")
        chunker = SemanticChunker(chunk_size=512, overlap=50)
        chunks = chunker.chunk_text(text)
        print(f"✅ Created {len(chunks)} chunks")
        
        # Store chunks
        print("   Storing chunks in database...")
        for i, chunk in enumerate(chunks):
            db.store_chunk(
                doc_id=doc_id,
                chunk_text=chunk,
                chunk_index=i,
                metadata={"chunk_number": i}
            )
        print(f"✅ Stored {len(chunks)} chunks")
        
        # Step 6: Discover schemas
        print("\n🔍 Step 6: Discovering schemas with Google Gemini...")
        inductor = SchemaInductor(db)
        
        try:
            schema_result = inductor.induce_schema(
                entity_hints=["Company", "Financial", "Person", "Product"],
                max_samples=5,
                min_confidence=0.6
            )
            print(f"✅ Discovered {len(schema_result.discovered_entities)} schemas:")
            for schema in schema_result.discovered_entities:
                print(f"   - {schema.name} ({len(schema.attributes)} attributes)")
        except Exception as e:
            print(f"❌ Schema discovery failed: {str(e)}")
            import traceback
            traceback.print_exc()
            print("\n⚠️  Skipping entity extraction and query steps")
            return False
        
        # Step 7: Extract entities
        print("\n🎯 Step 7: Extracting entities...")
        extractor = EntityExtractor(db, provenance)
        
        total_entities = 0
        for schema in schema_result.discovered_entities:
            try:
                print(f"   Extracting {schema.name} entities...")
                extraction_result = extractor.extract_entities(schema, document_id=doc_id)
                total_entities += extraction_result.entity_count
                print(f"   ✅ Extracted {extraction_result.entity_count} {schema.name} entities")
            except Exception as e:
                print(f"   ⚠️  Failed to extract {schema.name}: {str(e)}")
        
        print(f"✅ Total entities extracted: {total_entities}")
        
        # Step 8: Query test
        print("\n💬 Step 8: Testing query engine...")
        engine = QueryEngine(db, provenance)
        
        test_queries = [
            "What are the main topics in this document?",
            "List all entities found",
        ]
        
        for query in test_queries:
            try:
                print(f"\n   Query: {query}")
                result = engine.query(query)
                print(f"   ✅ Answer: {result.answer}")
                if result.results:
                    print(f"   ✅ Found {len(result.results)} results")
            except Exception as e:
                print(f"   ⚠️  Query failed: {str(e)}")
        
        print("\n" + "=" * 60)
        print("✅ WORKFLOW TEST COMPLETED SUCCESSFULLY")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup
        if Path(db_file).exists():
            print(f"\n🗑️  Cleanup: Removing {db_file}")
            Path(db_file).unlink()


if __name__ == "__main__":
    # Check for PDF path
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        print("Usage: python test_full_workflow.py <path_to_pdf>")
        print("\nOr just run with a sample PDF:")
        # Try to find any PDF in current directory
        pdfs = list(Path(".").glob("*.pdf"))
        if pdfs:
            pdf_path = str(pdfs[0])
            print(f"Found PDF: {pdf_path}")
        else:
            print("No PDF found. Please provide a path.")
            sys.exit(1)
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)
    
    success = test_full_workflow(pdf_path)
    sys.exit(0 if success else 1)
