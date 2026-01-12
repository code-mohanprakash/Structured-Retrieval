"""
Getting Started Example for StructRAG MCP

This script demonstrates the complete workflow:
1. Create sample documents
2. Ingest them
3. Discover schema
4. Query structured data
"""

import os
import tempfile
from pathlib import Path

# Sample sales call transcripts
SAMPLE_DOCS = [
    """
    SALES CALL TRANSCRIPT - Deal #001
    Date: 2024-01-15
    
    Company: Acme Corp
    Industry: Technology
    Contact: John Smith, CTO
    Phone: (555) 123-4567
    
    Deal Details:
    - Product: Enterprise Software License
    - Users: 100
    - Deal Value: $50,000
    - Status: Closed-Won
    - Close Date: 2024-01-15
    
    Notes: Customer needs annual support package. Strong technical fit.
    Next steps: Onboarding scheduled for Feb 1st.
    """,
    
    """
    SALES CALL TRANSCRIPT - Deal #002
    Date: 2024-01-20
    
    Company: Globex Industries
    Industry: Manufacturing
    Contact: Sarah Johnson, VP Operations
    Email: sarah@globex.com
    
    Deal Details:
    - Product: Cloud Platform Subscription
    - Users: 250
    - Deal Value: $125,000
    - Status: Closed-Won
    - Close Date: 2024-01-20
    
    Notes: Multi-year contract with 20% discount. Very satisfied customer.
    Referral potential high.
    """,
    
    """
    SALES CALL TRANSCRIPT - Deal #003
    Date: 2024-01-25
    
    Company: Initech Solutions
    Industry: Finance
    Contact: Bob Williams, CFO
    Phone: (555) 987-6543
    
    Deal Details:
    - Product: Data Analytics Suite
    - Users: 50
    - Deal Value: $35,000
    - Status: In Negotiation
    - Expected Close: 2024-02-15
    
    Notes: Price sensitivity. Considering competitor offers.
    Need to emphasize ROI and security features.
    """,
]


def create_sample_corpus(output_dir: str):
    """Create sample documents for testing"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    for i, content in enumerate(SAMPLE_DOCS, 1):
        file_path = Path(output_dir) / f"deal_{i:03d}.txt"
        file_path.write_text(content)
    
    print(f"✓ Created {len(SAMPLE_DOCS)} sample documents in {output_dir}")


def main():
    """Run the complete example workflow"""
    print("=" * 60)
    print("StructRAG MCP - Getting Started Example")
    print("=" * 60)
    print()
    
    # Step 1: Create sample data
    print("Step 1: Creating sample sales call transcripts...")
    temp_dir = tempfile.mkdtemp(prefix="structrag_example_")
    create_sample_corpus(temp_dir)
    print()
    
    # Step 2: Instructions for using with MCP
    print("Step 2: Use StructRAG MCP Server")
    print("-" * 60)
    print()
    print("To use this data with StructRAG MCP:")
    print()
    print("1. Start the MCP server:")
    print("   poetry run python -m structrag_mcp.server")
    print()
    print("2. In Claude Desktop, use the tools:")
    print()
    print(f"   Tool: ingest_corpus")
    print(f"   Args: input_path='{temp_dir}'")
    print()
    print("3. Discover schema:")
    print()
    print("   Tool: build_structure")
    print("   Args: entity_hints=['Deal', 'Company', 'Contact']")
    print("         max_samples=10")
    print()
    print("4. Query your data:")
    print()
    print("   Tool: query_structured")
    print("   Args: nl_query='What is the total value of closed-won deals?'")
    print()
    print("   Tool: query_structured")
    print("   Args: nl_query='Show me all deals grouped by industry'")
    print()
    print("   Tool: query_structured")
    print("   Args: nl_query='Which company has the largest deal?'")
    print()
    print("5. View provenance:")
    print()
    print("   Tool: audit")
    print("   Args: (leave empty for system summary)")
    print()
    print("-" * 60)
    print()
    
    # Step 3: Direct Python API example (without MCP)
    print("Step 3: Direct Python API (Optional)")
    print("-" * 60)
    print()
    print("You can also use StructRAG directly in Python:")
    print()
    print("""
from structrag_mcp.storage import DuckDBManager, ProvenanceTracker
from structrag_mcp.ingestion import TextParser, Chunker
from structrag_mcp.structure import SchemaInductor, EntityExtractor
from structrag_mcp.query import QueryEngine

# Initialize
db = DuckDBManager("./data/structrag.db")
provenance = ProvenanceTracker(db)

# Ingest document
parser = TextParser()
chunker = Chunker()
doc = parser.parse("deal_001.txt")
chunks = chunker.chunk(doc["text"], {})
# ... (insert into DB)

# Discover schema
inductor = SchemaInductor(db)
schema_result = inductor.induce_schema(
    entity_hints=["Deal", "Company"],
    max_samples=3
)

# Extract entities
extractor = EntityExtractor(db, provenance)
for entity_schema in schema_result.entities:
    results = extractor.extract_from_corpus(entity_schema)
    # ... (store in DB)

# Query
engine = QueryEngine(db, provenance)
result = engine.query("What's the average deal value?")
print(result.answer)
print(result.to_markdown())
    """)
    print()
    print("-" * 60)
    print()
    
    print("✅ Example complete!")
    print()
    print(f"Sample data location: {temp_dir}")
    print()
    print("Next steps:")
    print("1. Set OPENAI_API_KEY in .env")
    print("2. Configure Claude Desktop to use StructRAG MCP")
    print("3. Try the workflow above!")
    print()


if __name__ == "__main__":
    main()
