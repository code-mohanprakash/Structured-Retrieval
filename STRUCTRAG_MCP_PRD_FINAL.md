# StructRAG MCP - Complete Product Requirements Document
## Production-Ready Structured Retrieval-Augmented Generation via MCP

**Version:** 1.0  
**Owner:** Mohan Prakash Jeyasankar  
**Status:** Approved for Build  
**Target Launch:** February 2026 (MVP)  
**Last Updated:** January 12, 2026

---

## Executive Summary

**StructRAG MCP** is the first open-source Model Context Protocol server that unifies SQL databases and document RAG for aggregative analytics. It automatically discovers structure in unstructured documents and enables analytical queries (COUNT, AVG, SUM, TOP-N) that traditional RAG systems cannot handle.

**Market Position:** First mover in structured RAG MCP space with 6-12 month competitive advantage.

**Differentiation:** 
- Vanna AI + RAG capabilities
- Plug-and-play MCP integration
- Auto-schema discovery
- Full provenance/auditability

---

## Market Validation

### Current Market State (January 2026)

#### ✅ **Validated Gap**
- **500+ MCP servers exist** - ZERO do structured RAG over documents
- **Text-to-SQL leaders** (Vanna AI: 22k stars, Defog SQLCoder) have NO MCP integration
- **Document RAG tools** (Needle, Ragie, Vectara) have NO SQL/aggregation support
- **ThoughtSpot** (only competitor) announced MCP in Jan 2025 - enterprise-only, closed, expensive

#### 📈 **Market Opportunity**
- RevOps/SalesOps analytics: Multi-billion dollar market (Gong, Chorus.ai validate this)
- 1000s of companies manually analyze sales calls, support tickets, customer feedback
- No open-source solution exists for "analytical questions over document collections"

#### 🎯 **Target Users (Validated)**
1. **AI Product Engineers** - Building agentic workflows
2. **RevOps/SalesOps Teams** - Analyzing sales data
3. **Data/Analytics Teams** - Document analytics at scale
4. **Startup Builders** - Need fast document insights

---

## Problem Statement

**Current RAG Limitations:**
```
❌ "How many deals did we win last quarter?" → Cannot count across documents
❌ "Average deal size by industry?" → Cannot aggregate
❌ "Top 3 loss reasons?" → Cannot rank/group
❌ "Show me proof" → No source traceability
```

**Why Existing Solutions Fail:**

| Tool | Problem |
|------|---------|
| Vector RAG | Returns passages, not aggregated facts |
| Text-to-SQL | Requires pre-modeled database |
| LangChain/LlamaIndex | Requires manual coding/assembly |
| Traditional BI | Cannot ingest unstructured docs |

**StructRAG MCP Solution:**
```
✅ Ingest 1000 PDFs → Auto-discover schema → Answer "What's the avg?" → Get answer + sources
```

---

## Product Vision

### Core Value Proposition
> "Turns unstructured documents into a queryable analytical database automatically. No SQL skills required. Full provenance included."

### Strategic Positioning
```
Traditional RAG: "Where is the answer?" (single-passage retrieval)
StructRAG MCP: "What does the data say?" (aggregative analytics)
```

**Tagline:** "DuckDB + RAG had a baby. It speaks MCP."

---

## Goals & Success Metrics

### Phase 1 Goals (MVP - 3 weeks)
1. ✅ Launch functional MCP server
2. ✅ Ingest 1000 docs in <5 minutes
3. ✅ 80%+ schema accuracy (user-guided)
4. ✅ 10 correct analytical queries in demo
5. ✅ 100+ GitHub stars in month 1

### Phase 2 Goals (3 months)
1. Auto-schema induction with 85%+ accuracy
2. 1000+ active users
3. Featured in Anthropic MCP directory
4. Partnership with Cursor/Claude Desktop

### Success Metrics (KPIs)
```
- Time-to-first-query: <5 minutes (setup to answer)
- Query correctness: >90% for COUNT/AVG/SUM
- Schema acceptance rate: >80% (user validates auto-schema)
- Developer adoption: 500+ npm installs/month (Month 3)
- Provenance accuracy: 100% (every answer traced to sources)
```

---

## Technical Architecture (Final Decisions)

### Stack Overview
```
┌─────────────────────────────────────────────────────────────┐
│                    MCP CLIENT (Claude/Cursor)                │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  StructRAG MCP Server                        │
│  (Python 3.11+ with FastMCP framework)                       │
├──────────────────────────────────────────────────────────────┤
│  Tools: ingest_corpus | build_structure | explain_schema |  │
│         query_structured | query_hybrid | audit              │
└──────────────────────────┬──────────────────────────────────┘
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
┌──────▼────────┐  ┌───────▼────────┐  ┌──────▼──────┐
│   DuckDB      │  │   ChromaDB     │  │  LLM APIs   │
│ (Structured)  │  │  (Semantic)    │  │ (OpenAI/    │
│ SQL Analytics │  │  Vector Store  │  │  Anthropic) │
└───────────────┘  └────────────────┘  └─────────────┘
```

### Component Decisions

#### 1. **Database: DuckDB** ✅
**Why DuckDB over PostgreSQL:**
- **10-100x faster** for analytical queries (columnar storage)
- **Zero config** - single file or in-memory
- **Embedded** - no separate server process
- **Perfect for 10K-1M documents** (MVP scale)
- **Schema evolution** - instant ALTER TABLE
- **Arrow/Parquet native** - fast bulk loading

**When to switch to PostgreSQL:** Multi-writer concurrency, enterprise audit requirements (Phase 3+)

#### 2. **Vector Store: ChromaDB** ✅ (Lazy-Loaded)
**Why ChromaDB:**
- **Embedded** like DuckDB (no server)
- **MIT licensed** (commercial-friendly)
- **Metadata filtering** (filter by doc_id, date, source)
- **Python-native** with pandas integration

**Implementation Strategy:**
```python
class StructRAGEngine:
    def __init__(self):
        self.duckdb = duckdb.connect("structrag.db")
        self._chroma = None  # Lazy load
    
    @property
    def chroma(self):
        if self._chroma is None:
            self._chroma = chromadb.Client(...)
        return self._chroma
```

#### 3. **LLM Provider: Multi-Provider** ✅
```yaml
Primary: OpenAI GPT-4o (schema induction, query translation)
Fallback: Anthropic Claude 3.5 Sonnet
Cost-Effective: GPT-4o-mini (entity extraction, answer generation)
Local Option: Ollama (Llama 3.1) for privacy-sensitive use cases
```

**Task Assignments:**
- **Schema Induction:** GPT-4o (complex reasoning)
- **Entity Extraction:** GPT-4o-mini (high volume)
- **Query Translation:** GPT-4o (correctness critical)
- **Answer Generation:** GPT-4o-mini (fast summarization)

#### 4. **MCP Framework: FastMCP** ✅
**Why FastMCP over vanilla Python SDK:**
```python
from fastmcp import FastMCP

mcp = FastMCP("StructRAG")

@mcp.tool()
async def query_structured(question: str) -> dict:
    """Ask analytical questions over documents"""
    # 5 lines of code vs 50 with vanilla SDK
```

**Advantages:**
- Pythonic decorators
- Auto type validation (Pydantic)
- Built-in error handling
- 10x less boilerplate

---

## Feature Requirements (Detailed)

### MVP Feature Set (Phase 1: 3 Weeks)

#### 1. **Corpus Ingestion** ✅
```python
@mcp.tool()
async def ingest_corpus(
    files: List[str],
    source_type: Literal["pdf", "csv", "text", "transcript"],
    metadata: Optional[dict] = None
) -> dict:
    """
    Upload documents for analysis
    
    Supported:
    - PDF documents (pypdf)
    - CSV/TSV files (pandas)
    - Plain text/Markdown
    - Transcripts (JSON/TXT)
    
    Returns:
    - doc_count: Number of documents ingested
    - chunk_count: Number of chunks created
    - storage_size: Size in MB
    """
```

**Implementation:**
- **Chunking:** Semantic chunking (512 tokens, 50 overlap)
- **Metadata:** Extract filename, date, author, source
- **Storage:** DuckDB table + raw files in `/data/raw/`

#### 2. **Structure Induction** ✅
```python
@mcp.tool()
async def build_structure(
    strategy: Literal["auto", "guided", "custom"] = "guided",
    hints: Optional[dict] = None
) -> dict:
    """
    Discover entities and schema from documents
    
    Strategy:
    - auto: LLM fully infers schema (Phase 2)
    - guided: User provides entity hints, LLM fills details
    - custom: User provides full schema (JSON)
    
    Hints Example:
    {
        "entities": ["Deal", "Company", "Contact"],
        "sample_docs": [0, 10, 50]  # Doc indices to analyze
    }
    
    Returns:
    - schema: Inferred database schema (SQL DDL)
    - entities: List of entities discovered
    - confidence: Per-field confidence scores
    """
```

**MVP Implementation (Guided Mode):**
```python
# User provides: ["Deal", "Company"]
# System prompts GPT-4o:
"""
Analyze these 10 sample documents.
Given entity types: Deal, Company

Extract:
1. All attributes for each entity
2. Data types (text, number, date, boolean)
3. Relationships between entities

Return structured JSON schema.
"""
```

#### 3. **Schema Explanation** ✅
```python
@mcp.tool()
async def explain_schema() -> dict:
    """
    Show discovered database structure
    
    Returns:
    - tables: List of tables with columns
    - relationships: Foreign keys/links
    - sample_data: 5 rows per table
    - statistics: Row counts, completeness
    """
```

#### 4. **Structured Querying** ✅
```python
@mcp.tool()
async def query_structured(
    question: str,
    format: Literal["natural", "table", "json"] = "natural"
) -> dict:
    """
    Ask analytical questions (COUNT, AVG, SUM, TOP-N, GROUP BY)
    
    Examples:
    - "How many deals closed last quarter?"
    - "Average deal size by industry"
    - "Top 5 customers by revenue"
    
    Returns:
    - answer: Natural language response
    - data: Structured results (table/json)
    - sql: SQL query executed (for transparency)
    - sources: Document citations with excerpts
    - confidence: Answer confidence score
    """
```

**Query Translation Pipeline:**
```
1. Classify query type (count/avg/filter/group)
2. Translate to DuckDB SQL with safety checks
3. Execute with timeout guards
4. Format results + citations
5. Generate natural language answer
```

#### 5. **Hybrid Querying** (Phase 2)
```python
@mcp.tool()
async def query_hybrid(question: str) -> dict:
    """
    Combine structured + semantic search
    
    Example: "Top 3 deals mentioning 'quick implementation'"
    → Structured: TOP 3, ORDER BY deal_size
    → Semantic: Vector search for "quick implementation"
    → Merge: Ranked results with semantic filtering
    """
```

#### 6. **Audit & Provenance** ✅
```python
@mcp.tool()
async def audit(query_id: str) -> dict:
    """
    Trace any answer back to source documents
    
    Returns:
    - query: Original question
    - sql_executed: Actual SQL run
    - sources: List of source documents with page numbers
    - extracted_data: Raw data from each source
    - timestamp: When query was executed
    """
```

---

## Data Model

### DuckDB Schema (Auto-Generated Example)
```sql
-- Metadata table (always exists)
CREATE TABLE documents (
    doc_id TEXT PRIMARY KEY,
    filename TEXT,
    source_type TEXT,
    ingested_at TIMESTAMP,
    chunk_count INTEGER,
    metadata JSON
);

-- Auto-discovered entity tables (example: sales calls)
CREATE TABLE deals (
    deal_id TEXT PRIMARY KEY,
    company_name TEXT,
    deal_size DECIMAL(12,2),
    stage TEXT,
    outcome TEXT,  -- won/lost/pending
    close_date DATE,
    industry TEXT,
    doc_id TEXT,  -- Source document
    confidence FLOAT,
    FOREIGN KEY (doc_id) REFERENCES documents(doc_id)
);

CREATE TABLE loss_reasons (
    reason_id TEXT PRIMARY KEY,
    deal_id TEXT,
    reason_category TEXT,
    reason_text TEXT,
    doc_id TEXT,
    FOREIGN KEY (deal_id) REFERENCES deals(deal_id)
);

-- Provenance table (links results to sources)
CREATE TABLE query_provenance (
    query_id TEXT PRIMARY KEY,
    question TEXT,
    sql_executed TEXT,
    result_json JSON,
    source_docs JSON,  -- Array of doc_ids
    executed_at TIMESTAMP
);
```

### ChromaDB Collections (Lazy-Loaded)
```python
# Collection: document_chunks
{
    "ids": ["doc1_chunk0", "doc1_chunk1", ...],
    "embeddings": [...],
    "metadatas": [
        {
            "doc_id": "doc1",
            "chunk_index": 0,
            "text": "Deal with Acme Corp...",
            "entities": ["deal_123", "company_456"]
        }
    ]
}
```

---

## Technical Implementation Plan

### Phase 1: MVP (3 Weeks)

#### Week 1: Foundation
```bash
Day 1-2: Project Setup
- Initialize Python project with Poetry
- Install dependencies (fastmcp, duckdb, pypdf, pydantic)
- Setup MCP server scaffold
- Create basic file structure

Day 3-4: Ingestion Pipeline
- PDF parser (pypdf)
- CSV parser (pandas)
- Text chunker (semantic boundaries)
- DuckDB storage layer

Day 5-7: Schema Induction (Guided Mode)
- LLM prompt engineering for schema discovery
- GPT-4o integration (OpenAI SDK)
- Schema validation (Pydantic models)
- DuckDB table creation from schema
```

#### Week 2: Query Engine
```bash
Day 8-10: Query Router & Translator
- Query classification (rule-based initially)
- NL → SQL translator (GPT-4o)
- SQL safety validator (prevent DROP, etc.)
- DuckDB executor with timeouts

Day 11-12: Answer Generator
- Result → Natural language (GPT-4o-mini)
- Citation extractor
- Confidence scoring

Day 13-14: Provenance Layer
- Query logging to DuckDB
- Source tracing
- Audit trail implementation
```

#### Week 3: Integration & Testing
```bash
Day 15-16: MCP Tools Implementation
- Wire up all 6 tools
- FastMCP decorator implementation
- Error handling & validation

Day 17-18: Testing & Demo
- Unit tests (pytest)
- Integration tests (full pipeline)
- Create demo dataset (100 sales call transcripts)
- Record demo video

Day 19-21: Documentation & Launch
- README with setup instructions
- Example notebook
- Publish to npm/GitHub
- Announcement blog post
```

### Phase 2: Advanced Features (Months 2-3)

#### Month 2: Hybrid Queries
- ChromaDB integration
- Semantic + structured query merging
- Vector index optimization

#### Month 3: Auto-Schema & Polish
- Full auto schema induction (no user hints)
- Multi-schema support
- Performance optimizations
- Enterprise features (RBAC)

---

## Technology Stack Summary

### Core Dependencies
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastmcp = "^0.3.0"              # MCP framework
duckdb = "^1.1.3"               # Analytical database
chromadb = "^0.4.22"            # Vector store (lazy)
openai = "^1.12.0"              # LLM provider
anthropic = "^0.18.0"           # Fallback LLM
pypdf = "^3.17.0"               # PDF parsing
pandas = "^2.1.0"               # CSV handling
pydantic = "^2.5.0"             # Data validation
uvicorn = "^0.25.0"             # ASGI server (if HTTP)

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.0"
pytest-asyncio = "^0.21.0"
black = "^23.0.0"
ruff = "^0.1.0"
```

### External APIs
```bash
# Required
OPENAI_API_KEY=sk-...           # Primary LLM

# Optional
ANTHROPIC_API_KEY=sk-ant-...    # Fallback LLM
OLLAMA_ENDPOINT=http://localhost:11434  # Local option
```

---

## File Structure
```
structrag-mcp/
├── pyproject.toml              # Poetry config
├── README.md                   # Setup & usage
├── .env.example                # API key template
├── LICENSE                     # MIT
│
├── src/
│   └── structrag_mcp/
│       ├── __init__.py
│       ├── server.py           # MCP entry point
│       │
│       ├── ingestion/
│       │   ├── parsers.py      # PDF, CSV, text parsers
│       │   ├── chunker.py      # Semantic chunking
│       │   └── metadata.py     # Metadata extraction
│       │
│       ├── structure/
│       │   ├── induction.py    # Schema discovery (LLM)
│       │   ├── extractor.py    # Entity extraction
│       │   └── schema.py       # Schema management
│       │
│       ├── query/
│       │   ├── router.py       # Query classification
│       │   ├── translator.py   # NL → SQL (LLM)
│       │   ├── executor.py     # Safe SQL execution
│       │   └── generator.py    # Results → NL
│       │
│       ├── storage/
│       │   ├── duckdb_manager.py  # DuckDB operations
│       │   ├── vector_store.py    # ChromaDB wrapper
│       │   └── provenance.py      # Audit logging
│       │
│       └── llm/
│           ├── provider.py     # LLM abstraction
│           └── prompts.py      # Prompt templates
│
├── examples/
│   ├── sales_analysis.py       # Win-loss demo
│   ├── sample_data/
│   │   └── sales_calls_100.csv # Demo dataset
│   └── notebooks/
│       └── getting_started.ipynb
│
├── tests/
│   ├── test_ingestion.py
│   ├── test_structure.py
│   ├── test_query.py
│   └── fixtures/
│       └── test_docs/
│
└── data/                       # Created at runtime
    ├── structrag.db            # DuckDB file
    ├── chromadb/               # Vector store
    ├── raw/                    # Uploaded files
    └── audit/                  # Query logs
```

---

## Go-to-Market Strategy

### Launch Plan (Week 3)

#### 1. **GitHub Launch**
- Publish to `github.com/mohan/structrag-mcp`
- Comprehensive README with 3-minute quickstart
- Demo video (2 min): "From 100 PDFs to insights in 60 seconds"
- Tag: `v0.1.0-mvp`

#### 2. **Distribution**
```bash
# npm (for MCP ecosystem)
npm install -g @structrag/mcp-server

# PyPI (for Python users)
pip install structrag-mcp

# Docker (for ease of use)
docker run -p 8080:8080 structrag/mcp-server
```

#### 3. **Community Engagement**
- Post to [Anthropic MCP GitHub](https://github.com/modelcontextprotocol/servers)
- Post to [awesome-mcp-servers](https://github.com/appcypher/awesome-mcp-servers)
- Reddit: r/ClaudeAI, r/MachineLearning, r/LocalLLaMA
- Twitter/X: Tag @AnthropicAI, @ClaudeAI
- Hacker News: "Show HN: StructRAG MCP - Structured RAG for analytical queries"

#### 4. **Content Marketing**
- Blog: "Why Vector RAG Can't Count: Introducing Structured RAG"
- Tutorial: "Build a Win-Loss Analyzer in 10 Minutes"
- Comparison: "StructRAG MCP vs Vanna AI vs LangChain SQL"

### Target Metrics (Month 1)
- 100+ GitHub stars
- 500+ npm downloads
- 10+ community contributions
- Featured in 1 newsletter (e.g., TLDR AI)

---

## Competitive Positioning

### Direct Competitors
| Competitor | Strengths | Weaknesses | Our Advantage |
|-----------|-----------|------------|---------------|
| **Vanna AI** | Mature, 22k stars, production users | No MCP, no RAG, requires DB | We do documents + MCP |
| **ThoughtSpot MCP** | Enterprise backing, brand | Closed, expensive, Jan 2025 launch | We're open-source, free |
| **LangChain SQL** | Ecosystem, comprehensive | Requires coding, no MCP | Plug-and-play |
| **Defog SQLCoder** | Best accuracy, local option | No MCP, no document ingestion | We do both |

### Key Differentiators
1. **Only open-source structured RAG MCP server**
2. **Auto-schema discovery** (no manual DB modeling)
3. **Full provenance** (every answer traced to sources)
4. **Plug-and-play** (works with Claude Desktop immediately)

---

## Risk Mitigation

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Schema hallucination | High | High | Start with guided mode (user hints), Phase 2 auto |
| Query mistranslation | Medium | High | SQL validator, GPT-4o (best accuracy), human-in-loop |
| Performance at scale | Medium | Medium | DuckDB handles 10M rows easily, profile early |
| LLM API costs | Low | Medium | Cache aggressively, use mini models where possible |

### Market Risks

| Risk | Mitigation |
|------|------------|
| **Vanna adds MCP** | Ship fast (3 weeks), establish brand, build community moat |
| **LangChain productizes** | Target startups (they target enterprise), move faster |
| **Low adoption** | Demo-driven marketing, solve real pain (RevOps teams) |

---

## Success Criteria (MVP)

### Must Have ✅
- [ ] Ingest 1000 docs in <5 minutes
- [ ] Schema induction with 80%+ accuracy (guided mode)
- [ ] 10 correct analytical queries in demo
- [ ] Full provenance for every answer
- [ ] Works with Claude Desktop out-of-box
- [ ] <5 minute setup (pip install → first query)

### Should Have
- [ ] ChromaDB hybrid queries (Phase 1.5)
- [ ] Multi-LLM support (OpenAI + Anthropic)
- [ ] Docker deployment option
- [ ] Jupyter notebook examples

### Could Have (Phase 2)
- [ ] Auto schema induction (no hints)
- [ ] Web UI for schema editing
- [ ] Multi-user support
- [ ] Real-time ingestion

---

## Appendix

### Research References
- Market Analysis: `/research_output/structrag_mcp_market_analysis.md`
- Competitive Landscape: Vanna AI (22k stars), ThoughtSpot MCP (Jan 2025)
- MCP Ecosystem: 500+ servers, Linux Foundation backed (Dec 2024)

### Related Work
- **Structured RAG Paper** (2024): [arxiv.org/abs/2410.05779](https://arxiv.org/abs/2410.05779)
- **FastMCP Framework**: [github.com/jlowin/fastmcp](https://github.com/jlowin/fastmcp)
- **DuckDB SQL**: [duckdb.org/docs](https://duckdb.org/docs)

---

## Approval & Sign-Off

**Status:** ✅ **APPROVED FOR BUILD**

**Build Start Date:** January 12, 2026  
**Target MVP Launch:** February 2, 2026 (3 weeks)

**Next Steps:**
1. Initialize Python project (Poetry)
2. Setup MCP server scaffold
3. Implement ingestion pipeline (Week 1)

**Decision Log:**
- ✅ DuckDB over PostgreSQL (analytical performance)
- ✅ FastMCP over vanilla SDK (developer experience)
- ✅ Guided schema induction for MVP (de-risk hallucination)
- ✅ OpenAI GPT-4o primary LLM (best accuracy)
- ✅ 3-week sprint to MVP (speed to market)

---

**Let's build this. 🚀**
