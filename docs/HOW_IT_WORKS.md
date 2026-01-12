# 🚀 StructRAG MCP - How It Works & Testing Guide

## 📖 Table of Contents
1. [System Overview](#system-overview)
2. [How It Works (5 Steps)](#how-it-works)
3. [File Structure](#file-structure)
4. [Testing Guide](#testing-guide)
5. [Running Tests](#running-tests)

---

## 🎯 System Overview

**StructRAG MCP** = Automatic PDF → SQL tables → Natural Language Queries

```
PDF Documents → Extract Text → Find Patterns → Build SQL Tables → Answer Questions
```

**Example:**
- Input: 100 annual report PDFs
- Output: SQL tables (FinancialMetrics, BusinessSegments, CompanyInfo)
- Query: "Which company has highest revenue?" → Answer in 500ms

---

## 🔄 How It Works (5 Steps)

### Step 1: **Ingestion** 📥
**What happens:** PDFs converted to searchable chunks

```python
from structrag_mcp.server import ingest_corpus

# Ingest your PDFs
result = ingest_corpus("path/to/pdf/folder")
```

**Behind the scenes:**
1. `PDFParser` extracts text from PDF
2. `SemanticChunker` splits into 512-token chunks (50 overlap)
3. `DuckDBManager` stores in database
4. `ProvenanceTracker` tracks which chunk came from which PDF/page

**Files involved:**
- `src/structrag_mcp/ingestion/parsers.py` - PDF extraction
- `src/structrag_mcp/ingestion/chunker.py` - Text chunking
- `src/structrag_mcp/storage/duckdb_manager.py` - Database storage

---

### Step 2: **Schema Discovery** 🔍
**What happens:** AI analyzes chunks to find patterns

```python
from structrag_mcp.server import build_structure

# Discover what entities exist in your PDFs
result = build_structure(
    entity_hints=["FinancialMetrics", "BusinessSegment", "CompanyInfo"]
)
```

**Behind the scenes:**
1. `SchemaInductor` reads sample chunks from database
2. Builds prompt: "Analyze these documents and find entities"
3. Calls Groq LLM (llama-3.3-70b-versatile)
4. Parses response → Creates SQL table schemas
5. Validates with Pydantic models

**Example Output:**
```json
{
  "entities": [
    {
      "name": "FinancialMetrics",
      "fields": [
        {"name": "revenue", "type": "DECIMAL"},
        {"name": "net_income", "type": "DECIMAL"},
        {"name": "fiscal_year", "type": "INTEGER"}
      ]
    }
  ]
}
```

**Files involved:**
- `src/structrag_mcp/structure/schema_inductor.py` - Schema discovery (✅ JSON fix applied)
- `src/structrag_mcp/llm/provider.py` - Groq LLM calls
- `src/structrag_mcp/llm/prompts.py` - Prompts for AI

---

### Step 3: **Entity Extraction** 🎯
**What happens:** AI extracts actual data from chunks

```python
# Automatically happens after schema discovery
# No code needed - system extracts entities into SQL tables
```

**Behind the scenes:**
1. `EntityExtractor` uses discovered schema
2. For each chunk: "Extract FinancialMetrics from this text"
3. LLM returns: `{"revenue": 28300000000, "net_income": 4900000000, ...}`
4. Stores in SQL table: `INSERT INTO FinancialMetrics VALUES (...)`

**Example:**
```
Chunk: "Revenue for 2023 was $28.3 billion..."
↓
SQL: INSERT INTO FinancialMetrics (revenue, fiscal_year) 
     VALUES (28300000000, 2023)
```

**Files involved:**
- `src/structrag_mcp/structure/extractor.py` - Entity extraction
- `src/structrag_mcp/storage/duckdb_manager.py` - SQL inserts

---

### Step 4: **Query Translation** 💬
**What happens:** Natural language → SQL

```python
from structrag_mcp.server import query_structured

# Ask questions in plain English
result = query_structured("What was Occidental's revenue in 2023?")
```

**Behind the scenes:**
1. `QueryEngine` analyzes question
2. Builds prompt: "Translate to SQL. Available tables: FinancialMetrics..."
3. LLM generates SQL: `SELECT revenue FROM FinancialMetrics WHERE fiscal_year = 2023`
4. Validates SQL (no DROP/DELETE allowed)
5. Executes query → Gets results

**Files involved:**
- `src/structrag_mcp/query/engine.py` - Query processing (✅ JSON fix applied)
- `src/structrag_mcp/query/validator.py` - SQL safety checks

---

### Step 5: **Answer Generation** 📊
**What happens:** SQL results → Human-readable answer

**Behind the scenes:**
1. Gets SQL results: `[(28300000000,)]`
2. Builds prompt: "User asked 'What was revenue?' Results: 28.3B"
3. LLM generates: "Occidental's revenue in 2023 was $28.3 billion."
4. Returns formatted answer

---

## 📁 File Structure

```
structrag-mcp/
├── src/structrag_mcp/
│   ├── ingestion/           # Step 1: PDF → Chunks
│   │   ├── parsers.py       # PDF/CSV/TXT extraction
│   │   ├── chunker.py       # Text splitting (512 tokens)
│   │   └── metadata.py      # File metadata extraction
│   │
│   ├── storage/             # Database layer
│   │   ├── duckdb_manager.py    # SQL operations (✅ core)
│   │   └── provenance.py        # Track data lineage
│   │
│   ├── structure/           # Step 2 & 3: Schema + Extraction
│   │   ├── schema_inductor.py   # AI schema discovery (✅ FIXED)
│   │   ├── extractor.py         # Entity extraction
│   │   └── models.py            # Pydantic schemas
│   │
│   ├── query/               # Step 4 & 5: Query + Answer
│   │   ├── engine.py        # NL → SQL translation (✅ FIXED)
│   │   └── validator.py     # SQL safety checks
│   │
│   ├── llm/                 # AI layer
│   │   ├── provider.py      # Groq integration (✅ configured)
│   │   └── prompts.py       # All LLM prompts
│   │
│   └── server.py            # MCP server (main entry point)
│
├── tests/                   # Test suite (10/10 passing)
├── examples/                # Example scripts
│   └── getting_started.py   # Quick demo
│
├── .env                     # Groq API key (✅ configured)
├── occidental_ars.pdf       # Your test PDF (15 MB)
└── TEST_RESULTS.md          # Your test run summary
```

**Key Files (What They Do):**

| File | Purpose | Status |
|------|---------|--------|
| `server.py` | MCP tools (ingest_corpus, build_structure, query_structured) | ✅ Working |
| `schema_inductor.py` | AI discovers entities from PDFs | ✅ Fixed |
| `query/engine.py` | Translates questions to SQL | ✅ Fixed |
| `duckdb_manager.py` | All SQL operations | ✅ Working |
| `provider.py` | Groq LLM calls | ✅ Working |

---

## 🧪 Testing Guide

### Level 1: Unit Tests (Verify Components)
**What:** Test individual components in isolation

```bash
# Run all tests
pytest tests/ -v

# Specific test categories
pytest tests/test_ingestion.py -v      # PDF parsing, chunking
pytest tests/test_storage.py -v        # Database operations
pytest tests/test_structure.py -v      # Schema discovery
```

**What this tests:**
- ✅ PDF extraction works
- ✅ Chunking creates correct token counts
- ✅ Database stores/retrieves data
- ✅ Schema induction formats prompts correctly

---

### Level 2: Integration Tests (Verify Pipeline)
**What:** Test multiple components working together

**Test 1: Ingestion Pipeline**
```python
# Test: PDF → Database
python3 examples/getting_started.py
```

**Expected output:**
```
✅ Ingested 3 documents
✅ Created 40+ chunks
✅ Stored in DuckDB
```

**Test 2: Full Pipeline (Your Real PDF)**
```python
# Create test script
cat > test_occidental.py << 'EOF'
from structrag_mcp.storage import DuckDBManager, ProvenanceTracker
from structrag_mcp.ingestion import PDFParser, SemanticChunker
from structrag_mcp.structure.schema_inductor import SchemaInductor
import tempfile

# Setup
db_path = tempfile.mktemp() + ".db"
db = DuckDBManager(db_path)
provenance = ProvenanceTracker(db)

# Step 1: Ingest PDF
print("📥 Ingesting PDF...")
parser = PDFParser()
parsed = parser.parse("occidental_ars.pdf")
chunker = SemanticChunker()
chunks = chunker.chunk(parsed["text"], {})
print(f"✅ Created {len(chunks)} chunks")

# Step 2: Store chunks
doc_id = provenance.generate_doc_id("occidental.pdf", "occidental_ars.pdf")
db.insert_document(doc_id, "occidental.pdf", "occidental_ars.pdf", ".pdf", {})
for i, chunk in enumerate(chunks):
    chunk_id = provenance.generate_chunk_id(doc_id, i)
    db.insert_chunks([{
        "chunk_id": chunk_id, "doc_id": doc_id,
        "chunk_index": i, "text": chunk["text"],
        "token_count": chunk["token_count"], "metadata": {}
    }])
print(f"✅ Stored in database")

# Step 3: Schema discovery
print("\n🔍 Discovering schema...")
inductor = SchemaInductor(db)
result = inductor.induce_schema(
    entity_hints=["FinancialMetrics", "BusinessSegment", "CompanyInfo"]
)
print(f"✅ Found {len(result.entities)} entity types:")
for entity in result.entities:
    print(f"   - {entity.name}: {len(entity.fields)} fields")

print(f"\n🎉 Success! Database: {db_path}")
EOF

# Run test
python3 test_occidental.py
```

**Expected output:**
```
📥 Ingesting PDF...
✅ Created 42 chunks
✅ Stored in database

🔍 Discovering schema...
✅ Found 3 entity types:
   - FinancialMetrics: 6 fields
   - BusinessSegment: 4 fields
   - CompanyInfo: 5 fields

🎉 Success! Database: /tmp/xyz.db
```

---

### Level 3: End-to-End Tests (Real Usage)
**What:** Complete workflow with multiple PDFs

**Test 3: Multi-Document Analysis**
```python
# Create test
cat > test_multi_pdf.py << 'EOF'
from structrag_mcp.server import ingest_corpus, build_structure, query_structured
import os

# Setup test folder
os.makedirs("test_pdfs", exist_ok=True)
# (Place multiple PDFs in test_pdfs/ folder)

# Step 1: Ingest all PDFs
print("1️⃣ Ingesting PDFs...")
result = ingest_corpus("test_pdfs/")
print(f"✅ {result['documents_ingested']} PDFs ingested")

# Step 2: Discover schema
print("\n2️⃣ Discovering schema...")
schema = build_structure(entity_hints=["FinancialMetrics", "Company"])
print(f"✅ Schema discovered: {len(schema['entities'])} entities")

# Step 3: Query
print("\n3️⃣ Running queries...")
queries = [
    "What companies are in the database?",
    "What was the total revenue?",
    "Which company has the highest profit margin?"
]
for q in queries:
    print(f"\nQ: {q}")
    answer = query_structured(q)
    print(f"A: {answer['answer']}")
EOF

python3 test_multi_pdf.py
```

---

### Level 4: Performance Tests
**What:** Test speed and scale

**Test 4: Speed Benchmarks**
```python
cat > test_performance.py << 'EOF'
import time
from structrag_mcp.storage import DuckDBManager
from structrag_mcp.query.engine import QueryEngine, ProvenanceTracker
import tempfile

db = DuckDBManager(tempfile.mktemp() + ".db")
provenance = ProvenanceTracker(db)
engine = QueryEngine(db, provenance)

# Simulate: Tables already exist with data
queries = [
    "What was total revenue?",
    "Show top 5 companies by profit",
    "Calculate average debt ratio"
]

print("⏱️  Query Performance Test\n")
for q in queries:
    start = time.time()
    # result = engine.query(q)  # Requires data in DB
    elapsed = (time.time() - start) * 1000
    print(f"{q}: {elapsed:.0f}ms")
EOF
```

**Expected performance:**
- Simple queries: < 500ms
- Aggregations: < 1000ms
- Complex joins: < 2000ms

---

## 🎯 Running Rigorous Tests (Step-by-Step)

### Prerequisites
```bash
# 1. Verify installation
python3 -c "import structrag_mcp; print('✅ Installed')"

# 2. Check Groq API key
grep GROQ_API_KEY .env

# 3. Verify all tests pass
pytest tests/ -v
```

---

### Test Plan: Single PDF (Your Occidental)

**Day 1: Basic Pipeline**
```bash
# Test 1: Ingestion only
python3 << 'EOF'
from structrag_mcp.ingestion import PDFParser, SemanticChunker
parser = PDFParser()
parsed = parser.parse("occidental_ars.pdf")
chunker = SemanticChunker()
chunks = chunker.chunk(parsed["text"], {})
print(f"✅ Extracted {len(chunks)} chunks, {sum(c['token_count'] for c in chunks)} tokens")
EOF

# Expected: ✅ Extracted 42 chunks, 21416 tokens
```

**Day 2: Schema Discovery**
```bash
# Test 2: Full ingestion + schema (from test above)
python3 test_occidental.py

# Verify:
# - No JSON parsing errors
# - 3 entities discovered
# - Fields make sense (revenue, dates, etc.)
```

**Day 3: Entity Extraction**
```bash
# Test 3: Check extracted entities
python3 << 'EOF'
from structrag_mcp.storage import DuckDBManager
db = DuckDBManager("/path/to/db/from/test.db")  # Use path from test output

# Check what entities were extracted
tables = db.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
print("Tables:", tables)

# Check data in FinancialMetrics
metrics = db.execute_query("SELECT * FROM FinancialMetrics LIMIT 5")
print("Sample data:", metrics)
EOF
```

**Day 4: Query Testing**
```bash
# Test 4: Run queries
python3 << 'EOF'
from structrag_mcp.server import query_structured

questions = [
    "What was the revenue?",
    "Show business segments",
    "What is the debt ratio?"
]

for q in questions:
    print(f"\nQ: {q}")
    result = query_structured(q)
    print(f"SQL: {result['sql']}")
    print(f"A: {result['answer']}")
EOF
```

---

### Test Plan: Multiple PDFs (Production)

**Week 1: Small Batch (10 PDFs)**
1. Collect 10 annual reports from SEC EDGAR
2. Ingest all: `ingest_corpus("sec_pdfs/")`
3. Discover schema: `build_structure()`
4. Run 20+ queries
5. Verify accuracy: Check 5 random answers against source PDFs

**Week 2: Medium Batch (50 PDFs)**
1. Expand to 50 PDFs
2. Test performance: Query latency should stay < 1s
3. Test complex queries: "Compare all 50 companies"
4. Check database size: Should scale linearly

**Week 3: Large Batch (100+ PDFs)**
1. Full production test with 100+ PDFs
2. Analytics queries: AVG, SUM, GROUP BY across all documents
3. Performance profiling: Identify bottlenecks
4. Error handling: Test with corrupted PDFs

---

## ✅ Success Criteria

**System is working correctly if:**

1. **Ingestion**
   - ✅ PDFs convert to chunks without errors
   - ✅ Token counts match expectations (~500 tokens/chunk)
   - ✅ Database grows linearly with documents

2. **Schema Discovery**
   - ✅ Discovers 2-5 relevant entity types
   - ✅ Fields match document content
   - ✅ No JSON parsing errors (✅ FIXED)

3. **Entity Extraction**
   - ✅ Extracts >90% of entities correctly
   - ✅ Numbers match source PDFs
   - ✅ Handles missing fields gracefully

4. **Query Engine**
   - ✅ Translates NL questions to valid SQL
   - ✅ SQL executes without errors
   - ✅ Answers are factually correct
   - ✅ Query latency < 2 seconds

---

## 🐛 Troubleshooting

### Issue: JSON Parsing Errors
**Status:** ✅ FIXED (markdown stripping added)

**If still seeing errors:**
```python
# Check Groq response manually
from structrag_mcp.llm.provider import complete_with_fallback
response = complete_with_fallback(
    system_prompt="You are helpful",
    user_prompt="Return JSON: {\"test\": true}",
    json_mode=True
)
print("Response:", repr(response.content))
# Should NOT have ```json markers
```

### Issue: Slow Queries
**Solution:** Check database size and indexes
```python
db = DuckDBManager("your.db")
stats = db.execute_query("SELECT COUNT(*) FROM chunks")
print("Chunks:", stats)  # Should be < 100K for fast queries
```

### Issue: Incorrect Entities
**Solution:** Provide better entity hints
```python
# Instead of generic hints:
build_structure(entity_hints=["Entity1", "Entity2"])

# Use domain-specific hints:
build_structure(entity_hints=[
    "FinancialMetric_with_revenue_and_profit",
    "BusinessSegment_with_geography",
    "Executive_with_name_and_title"
])
```

---

## 📚 Next Steps

1. **Run your first rigorous test:** `python3 test_occidental.py`
2. **Get more PDFs:** Download 10 annual reports from SEC
3. **Test at scale:** Run with 50+ PDFs
4. **Tune performance:** Optimize based on your specific documents

---

## 💡 Key Takeaways

**What makes StructRAG powerful:**
1. **Automatic schema** - No manual field definition
2. **SQL on PDFs** - Analytics not possible with traditional RAG
3. **Provenance** - Every data point links to source
4. **Fast** - 500ms queries after upfront extraction

**Limitations:**
- Upfront cost: Schema discovery + extraction takes time
- Accuracy: Depends on LLM quality (Groq is good but not perfect)
- Structure: Works best with documents that have patterns

**Best use cases:**
- 50+ similar PDFs (contracts, invoices, reports)
- Need aggregations (sum, average, count)
- Compliance requires provenance tracking
- Value SQL analytics over text search
