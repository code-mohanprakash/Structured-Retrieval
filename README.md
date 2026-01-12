# StructRAG MCP

Transform PDFs into queryable SQL databases using AI. Extract structured data from unstructured documents automatically.

## What It Does

1. **Upload** a PDF (annual report, contract, invoice)
2. **AI discovers** hidden data structures (tables, entities)
3. **Extract** structured data into SQL tables
4. **Query** with natural language: "What was Q3 revenue?"

Traditional RAG finds keywords. **StructRAG finds patterns and builds databases.**

## 🌐 Try the Web Interface

**NEW:** Interactive web app - upload PDFs and query instantly!

```bash
# Install and run
pip install streamlit
./run_streamlit.sh
```

Opens at **http://localhost:8501** with drag-drop upload, chat interface, and table viewer.

[📖 Web App Guide](docs/STREAMLIT_APP.md)

## Quick Start

```bash
# Install
git clone https://github.com/code-mohanprakash/Structured-Retrieval.git
cd Structured-Retrieval
pip install -e .

# Add your Groq API key (free at console.groq.com)
echo "GROQ_API_KEY=gsk_YOUR_KEY_HERE" > .env

# Test it (2 minutes)
python quick_test.py
```

**Expected output:**
```
✅ Ingested: 42 chunks, 21,416 tokens
✅ Schema discovered: 3 entities
✅ All systems working!
```

## Real Example

**Input:** Occidental Petroleum Annual Report (15MB PDF)

**AI Discovered:**
- `FinancialMetrics` table (revenue, expenses, profit)
- `BusinessSegment` table (divisions, locations)
- `CompanyInfo` table (executives, acquisitions)

**Queries you can run:**
- "Show total revenue by quarter"
- "Which business segment has highest profit?"
- "List all acquisitions mentioned"

## How It Works

```
PDF → Smart Chunking → AI Analysis → SQL Tables → Query with Natural Language
```

1. **Chunk** PDF into semantic pieces (512 tokens each)
2. **Discover** patterns using Groq AI (llama-3.3-70b, ~1 second)
3. **Extract** structured data into DuckDB tables
4. **Query** using natural language → auto-converts to SQL

## Why Use This?

| Use Case | Example |
|----------|---------|
| **Financial Analysis** | Extract metrics from 100+ quarterly reports |
| **Legal Contracts** | Find all clauses mentioning payment terms |
| **Research Papers** | Compare methodologies across 50 studies |
| **Invoice Processing** | Auto-extract vendors, amounts, dates |

**The difference:** Aggregate and compare across documents. Traditional RAG can't do math or joins.

## Installation

**Requirements:**
- Python 3.11+
- Groq API key (free tier: 30 requests/min)

**Step-by-step:**
```bash
# 1. Clone
git clone https://github.com/code-mohanprakash/Structured-Retrieval.git
cd Structured-Retrieval

# 2. Install
pip install -e .

# 3. Configure API
cp .env.example .env
# Edit .env and add your Groq key

# 4. Verify
python quick_test.py
```

## Usage

### Basic Usage
```python
from structrag_mcp.ingestion import IngestionManager
from structrag_mcp.structure import SchemaInductor, EntityExtractor
from structrag_mcp.query import QueryEngine

# 1. Ingest PDF
manager = IngestionManager("my_db.db")
manager.ingest_pdf("annual_report.pdf")

# 2. Discover structure
inductor = SchemaInductor("my_db.db", llm_provider="groq")
schemas = inductor.discover_schemas()

# 3. Extract entities
extractor = EntityExtractor("my_db.db", llm_provider="groq")
extractor.extract_all_entities(schemas)

# 4. Query
engine = QueryEngine("my_db.db", llm_provider="groq")
result = engine.query("What was total revenue?")
print(result)
```

### Command Line
```bash
# Ingest documents
python examples/ingest_pdf.py report.pdf

# Discover schemas
python examples/discover_schema.py

# Query
python examples/query_example.py "Show revenue by quarter"
```

### With Claude Desktop (MCP)
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "structrag": {
      "command": "python",
      "args": ["-m", "structrag_mcp"],
      "env": {"GROQ_API_KEY": "gsk_YOUR_KEY_HERE"}
    }
  }
}
```

Then ask Claude: "Analyze the annual report in my database"

## Performance

**Tested with 15MB PDF:**
- Processing: 42 chunks in ~30 seconds
- Schema discovery: 3 entities in 1.1 seconds
- Queries: 500ms average response

**Costs (with Groq):**
- Schema discovery: ~$0.02 per document
- Queries: ~$0.001 per query
- Free tier: 30 requests/min (enough for testing)

## Documentation

📖 **[Complete Guide](docs/HOW_IT_WORKS.md)** - Full technical walkthrough  
🚀 **[Groq Setup](docs/GROQ_SETUP.md)** - API configuration  
✅ **[Test Results](docs/TEST_RESULTS.md)** - Real PDF examples  
📦 **[Distribution](docs/DISTRIBUTION_GUIDE.md)** - PyPI publishing

## Limitations

- Requires LLM for schema discovery (costs apply)
- Best with structured documents (reports, contracts)
- Not tested with 1000+ document collections yet
- Quality depends on LLM capabilities

## Roadmap

- [ ] Support for Word docs, Excel, CSV
- [ ] Pre-built schemas (financial, legal, research)
- [ ] Multi-document relationship detection
- [ ] Web UI for document management

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

**Ideas:**
- Add new document parsers
- Optimize chunking strategies
- Create domain-specific schema templates
- Improve query translation

## License

MIT License - Free for commercial use

## Support

- 🐛 **Bugs:** [GitHub Issues](https://github.com/code-mohanprakash/Structured-Retrieval/issues)
- 💬 **Questions:** [GitHub Discussions](https://github.com/code-mohanprakash/Structured-Retrieval/discussions)

---

**Built with:** Groq AI • DuckDB • Model Context Protocol
