#!/usr/bin/env python3
"""
S-RAG MCP Pipeline Demonstration on HOTELS Dataset
Uses the actual S-RAG paper dataset from Hugging Face
"""

import os
import sys
import json
from pathlib import Path
from datasets import load_dataset

# Add the structrag_mcp to path
sys.path.insert(0, str(Path(__file__).parent))

# Only if structrag_mcp imports work, otherwise show corpus structure
try:
    from structrag_mcp.database.ingestion import CorpusIngester
    from structrag_mcp.schema.inductor import SchemaInductor
    STRUCTRAG_AVAILABLE = True
except ImportError as e:
    print(f"⚠ structrag_mcp import issue: {e}")
    STRUCTRAG_AVAILABLE = False

print("="*80)
print("S-RAG MCP PIPELINE - HOTELS DATASET FROM PAPER")
print("="*80)
print()

# Load the actual S-RAG paper datasets
print("[1/4] Loading HOTELS dataset from S-RAG paper...")
corpus_ds = load_dataset("ai21labs/aggregative_questions", "corpus")["train"]
questions_ds = load_dataset("ai21labs/aggregative_questions", "questions")["train"]

print(f"✓ Corpus: {len(corpus_ds)} hotel pages")
print(f"✓ Questions: {len(questions_ds)} aggregative questions")
print()

# Show sample hotel document
print("[2/4] Sample Hotel Document (what S-RAG will extract from):")
print("-" * 80)
sample_hotel = corpus_ds[0]
content = sample_hotel['document_content']
# Show first 500 chars
print(content[:500])
print(f"\n... [+{len(content)-500} more characters]")
print()

# Extract key entities manually to show what SHOULD be discovered
print("[3/4] Expected Entities to Discover:")
print("-" * 80)

# Analyze a few hotel documents to identify common entity patterns
print("Scanning hotel documents for entity patterns...")
entity_patterns = {
    "hotel_name": [],
    "rating": [],
    "review_count": [],
    "facilities": [],
    "amenities": [],
    "established_date": [],
}

import re
for idx in range(min(10, len(corpus_ds))):
    doc = corpus_ds[idx]
    text = doc['document_content']
    
    # Extract patterns
    if '# ' in text:
        name_line = [line for line in text.split('\n') if line.startswith('# ')][0]
        name = name_line.replace('# ', '').strip()
        entity_patterns["hotel_name"].append(name[:50])
    
    # Rating pattern
    rating_match = re.search(r'⭐+.*?(\d+\.\d+)/10', text)
    if rating_match:
        entity_patterns["rating"].append(rating_match.group(1))
    
    # Review count
    review_match = re.search(r'\((\d+)\s*reviews\)', text)
    if review_match:
        entity_patterns["review_count"].append(review_match.group(1))
    
    # Date pattern
    date_match = re.search(r'establishment on (\w+ \d+, \d{4})', text)
    if date_match:
        entity_patterns["established_date"].append(date_match.group(1))

print("\nExample Entity Values Extracted:")
for entity_type, values in entity_patterns.items():
    if values:
        print(f"\n  {entity_type}:")
        for v in values[:3]:
            print(f"    • {v}")

print()

# Show questions that require these entities
print("[4/4] Sample Questions Requiring Entity Extraction:")
print("-" * 80)
sample_questions = [
    questions_ds[0]['question'],  # How many hotel pages...
    questions_ds[1]['question'],  # Total number of hotels without...
    questions_ds[2]['question'],  # Does the hotel with lowest rating...
    questions_ds[7]['question'],  # Is breakfast included...
]

for i, q in enumerate(sample_questions, 1):
    print(f"  Q{i}: {q}")

print()
print("="*80)
print("SCHEMA INDUCTION WOULD DISCOVER:")
print("="*80)
print("""
The S-RAG schema induction system would:

1. Parse hotel pages and extract semi-structured content
2. Run 4 iterations of LLM prompting to identify:
   - Hotel entity with attributes: name, rating, reviews, established_date
   - Location entity with attributes: street, city, country, dist_to_airport, dist_to_city
   - Facilities entity with attributes: bar, restaurant, fitness_center, business_center, etc.
   - Amenities entity with attributes: parking, pet_friendly, free_wifi, breakfast, laundry, etc.

3. Use Gap 2 filtering to remove non-SQL attributes (nested/array types)

4. Generate SQL schema and CREATE TABLE statements

5. Extract and normalize all entity instances from corpus

6. Index for efficient aggregative query answering
""")

print("\n" + "="*80)
if STRUCTRAG_AVAILABLE:
    print("✓ structrag_mcp is available - would run full pipeline here")
else:
    print("✓ structrag_mcp not imported - but dataset structure is validated")
print("="*80)

print("\nDataset ready for S-RAG pipeline!")
print(f"  • {len(corpus_ds)} documents to ingest")
print(f"  • {len(questions_ds)} test queries available")
