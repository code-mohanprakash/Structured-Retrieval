# 🚀 StructRAG MCP - Structured Retrieval-Augmented Generation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Convert PDFs to queryable SQL databases using AI-powered schema discovery.**

Traditional RAG returns text chunks. StructRAG extracts structured data into SQL tables, enabling analytics, aggregations, and complex queries across thousands of documents.

---

## 🎯 The Problem with Traditional RAG

```
User: "What's the total contract value across all documents?"
Traditional RAG: Returns text chunks... ❌ Can't aggregate
StructRAG: SELECT SUM(value) FROM Contracts → $15.2M ✅
```

---

## ✨ Features

- 🤖 **Automatic Schema Discovery** - AI analyzes your PDFs and discovers entity structures
- 📊 **SQL Analytics** - Run aggregations, JOINs, and complex queries across documents  
- ⚡ **Fast Queries** - 500ms query latency with Groq LLM
- 🔍 **Provenance Tracking** - Every data point links back to source document + page
- 🗄️ **DuckDB Backend** - Embedded analytical database, scales to 100K+ documents
- 🔌 **MCP Protocol** - Works with Claude Desktop and other MCP clients

---

## 📦 Installation

```bash
# Clone repository
git clone https://github.com/code-mohanprakash/Structured-Retrieval.git
cd Structured-Retrieval

# Install dependencies
pip install -e .

# Configure API keys
cp .env.example .env
# Edit .env and add your Groq API key
```

**Get a free Groq API key:** https://console.groq.com/keys

---

## ⚡ Quick Start

### Run Quick Test

```bash
python3 quick_test.py
```

Expected: ✅ All tests passed + entities discovered

### Python API Example

```python
from structrag_mcp.storage import DuckDBManager, ProvenanceTracker
from structrag_mcp.ingestion import PDFParser, SemanticChunker
from structrag_mcp.structure.schema_inductor import SchemaInductor

# Setup
db = DuckDBManager("./data/my_database.db")
provenance = ProvenanceTracker(db)

# Ingest PDFs
parser = PDFParser()
parsed = parser.parse("annual_report.pdf")

chunker = SemanticChunker()
chunks = chunker.chunk(parsed["text"], {})

# Store chunks
doc_id = provenance.generate_doc_id("report", "annual_report.pdf")
db.insert_document(doc_id, "report.pdf", "annual_report.pdf", ".pdf", {})
for i, chunk in enumerate(chunks):
    chunk_id = provenance.generate_chunk_id(doc_id, i)
    db.insert_chunks([{
        "chunk_id": chunk_id, "doc_id": doc_id,
        "chunk_index": i, "text": chunk["text"],
        "token_count": chunk["token_count"], "metadata": {}
    }])

# Discover schema automatically
inductor = SchemaInductor(db)
result = inductor.induce_schema(
    entity_hints=["FinancialMetrics", "BusinessSegment", "CompanyInfo"]
)

print(f"Discovered {len(result.entities)} entity types!")
```

### MCP Server (Use with Claude Desktop)

**1. Configure Claude Desktop:**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "structrag": {
      "command": "python",
      "args": ["-m", "structrag_mcp.server"],
      "env": {
        "GROQ_API_KEY": "your_groq_api_key_here"
      }
    }
  }
}
```

**2. Use in Claude Desktop:**
- Tools appear automatically
- "Ingest this folder of PDFs"
- "Build schema for contracts"
- "Query: What's the total revenue?"

---

## 🧪 Testing

### Quick Test
```bash
python3 quick_test.py
```

### Full Test Suite
```bash
pytest tests/ -v
```

Expected: 10/10 tests passing

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [READY_TO_USE.md](READY_TO_USE.md) | ⭐ Start here - Quick overview |
| [HOW_IT_WORKS.md](HOW_IT_WORKS.md) | Complete technical guide |
| [TEST_RESULTS.md](TEST_RESULTS.md) | Example test results |
| [DISTRIBUTION_GUIDE.md](DISTRIBUTION_GUIDE.md) | Publishing guide |

---

## 🎬 How It Works

### 5-Step Pipeline

```
1. INGESTION
   PDFs → Extract text → Semantic chunking (512 tokens)
   
2. SCHEMA DISCOVERY  
   AI analyzes patterns → Discovers entities automatically
   
3. ENTITY EXTRACTION
   AI extracts structured data → Populates SQL tables
   
4. QUERY TRANSLATION
   Natural language → SQL query generation
   
5. ANSWER GENERATION
   SQL results → Human-readable answer with provenance
```

---

## 💡 Use Cases

### Financial Analysis
```python
# Ingest 100 annual reports
# Query: "Which company has the highest revenue?"
# Query: "Show average profit margin by industry"  
# Query: "Compare year-over-year growth rates"
```

### Contract Analysis  
```python
# Ingest 500 vendor contracts
# Query: "What's the total contract value?"
# Query: "Which contracts expire in Q1 2024?"
# Query: "Show all contracts with auto-renewal clauses"
```

### Invoice Processing
```python
# Ingest 1000 invoices from multiple vendors
# Query: "Total amount invoiced this quarter?"
# Query: "Which vendor has the most unpaid invoices?"
# Query: "What's the average payment delay by vendor?"
```

---

## 🏗️ Architecture

```
src/structrag_mcp/
├── ingestion/          # PDF parsing, semantic chunking
├── storage/            # DuckDB operations, provenance tracking
├── structure/          # Schema discovery, entity extraction
├── query/              # NL → SQL translation, query engine
├── llm/                # Groq/OpenAI/Anthropic LLM providers
└── server.py           # MCP server implementation
```

---

## ⚙️ Configuration

### LLM Providers

**Groq (Default - Fast & Free):**
```bash
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
LLM_PROVIDER=groq
```

**OpenAI (Alternative):**
```bash
OPENAI_API_KEY=your_key_here  
OPENAI_MODEL=gpt-4o
LLM_PROVIDER=openai
```

**Anthropic (Alternative):**
```bash
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
LLM_PROVIDER=anthropic
```

---

## 📊 Performance Benchmarks

| Operation | Time | Notes |
|-----------|------|-------|
| PDF Ingestion | ~1 sec/MB | Includes parsing + chunking |
| Schema Discovery | 1-2 seconds | With Groq LLM |
| Entity Extraction | 2-3 sec/chunk | Parallel processing supported |
| Query Translation | 500-800 ms | Groq is very fast |
| SQL Execution | <100 ms | DuckDB optimized for analytics |

**Scales to:** 100K+ documents in single DuckDB database

---

## 🚀 What Makes StructRAG Powerful

### vs Traditional RAG

| Traditional RAG | StructRAG |
|-----------------|-----------|
| Returns text chunks | Returns structured data |
| Can't aggregate | SQL: SUM, COUNT, AVG, GROUP BY |
| Can't calculate | Math across documents |
| Slow for analytics | Fast with SQL indexes |
| No relationships | Foreign keys & JOINs |

### Key Advantages

1. **Automatic Schema** - No manual field definition needed
2. **SQL Power** - Full analytical SQL on unstructured PDFs
3. **Fast** - 500ms queries after upfront extraction
4. **Provenance** - Every data point traces to source page
5. **Scalable** - DuckDB handles millions of rows

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details

---

## 🙏 Acknowledgments

- **Groq** - Fast LLM inference (1-2 second responses)
- **DuckDB** - Embedded analytical database
- **FastMCP** - MCP server framework
- **PyPDF** - PDF text extraction

---

## 🔗 Links

- **Repository**: https://github.com/code-mohanprakash/Structured-Retrieval
- **Groq Console**: https://console.groq.com (Get free API key)
- **MCP Protocol**: https://modelcontextprotocol.io

---

## 💬 Support

- **Issues**: https://github.com/code-mohanprakash/Structured-Retrieval/issues
- **Documentation**: See repository docs folder

---

**Built with ❤️ for better document understanding**
