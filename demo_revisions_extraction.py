#!/usr/bin/env python3
"""
StructRAG MCP Demo: Extracting "Revisions of previous estimates" Entity

This script demonstrates the complete S-RAG pipeline:
1. PDF Ingestion: Parse Occidental Petroleum annual report
2. Chunking: Split into semantic chunks  
3. Schema Induction: Use LLM to discover entity structure
4. Entity Extraction: Extract instances of "Revisions of previous estimates"
"""

import sys
sys.path.insert(0, './src')

from structrag_mcp.ingestion.pdf_parser import PDFParser
from structrag_mcp.ingestion.chunker import SemanticChunker
from structrag_mcp.structure.schema_inductor import SchemaInductor
from structrag_mcp.storage.duckdb_manager import DuckDBManager

def main():
    print("\n" + "="*80)
    print("S-RAG ENTITY EXTRACTION: 'Revisions of previous estimates'")
    print("="*80 + "\n")
    
    # Step 1: Initialize database
    print("[Step 1/4] Initializing database...")
    db_manager = DuckDBManager("./data/revisions_demo.db")
    print("✓ DuckDB initialized\n")
    
    # Step 2: Parse and ingest PDF
    print("[Step 2/4] Parsing PDF (Occidental Petroleum 2022 10-K)...")
    parser = PDFParser()
    doc = parser.parse("./testdoc/occidental_ars.pdf")
    print(f"✓ Extracted {doc['page_count']} pages, {len(doc['text'])} chars\n")
    
    # Step 3: Chunk document
    print("[Step 3/4] Creating semantic chunks...")
    chunker = SemanticChunker()
    chunks = chunker.chunk(doc['text'])
    print(f"✓ Created {len(chunks)} chunks, {sum(c['token_count'] for c in chunks)} total tokens\n")
    
    # Store in database
    print("Storing in DuckDB...")
    db_manager.store_document(
        doc_id="oxy_2022_10k",
        filename="occidental_ars.pdf",
        content=doc['text'],
        chunks=chunks
    )
    print("✓ Document stored\n")
    
    # Step 4: Induce schema using S-RAG
    print("[Step 4/4] Running S-RAG schema induction...")
    print("Entity hint: 'Revisions of previous estimates'")
    print("(Running LLM-based schema discovery with 4 iterations...)\n")
    
    schema_inductor = SchemaInductor(db_manager)
    
    try:
        result = schema_inductor.induce_schema(
            entity_hints=["Revisions of previous estimates"],
            max_samples=15,
            min_confidence=0.5
        )
        
        print("✓ Schema induction COMPLETE\n")
        
        # Display results
        print("="*80)
        print("DISCOVERED ENTITY SCHEMA")
        print("="*80 + "\n")
        
        if result.entities:
            for entity in result.entities:
                print(f"📊 Entity: {entity.name}")
                print(f"   Confidence Score: {entity.confidence:.1%}")
                print(f"   Discovered Attributes ({len(entity.fields)}):")
                
                for i, field in enumerate(entity.fields[:15], 1):
                    print(f"     {i}. {field.name}")
                    print(f"        Type: {field.type}")
                    print(f"        Confidence: {field.confidence:.0%}")
                    if field.description:
                        print(f"        Description: {field.description[:60]}...")
                    print()
        else:
            print("⚠ No entities discovered in document")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
