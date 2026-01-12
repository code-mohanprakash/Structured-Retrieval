# 🌐 StructRAG Web Interface

Interactive web application for StructRAG - upload PDFs and query with natural language!

## Features

- 📤 **Drag & Drop Upload** - Upload PDFs directly in the browser
- 🤖 **Auto-Processing** - AI discovers schemas and extracts entities automatically
- 💬 **Chat Interface** - Ask questions in natural language
- 🗂️ **Table Viewer** - Browse discovered tables and schemas
- 📊 **Real-time Results** - See query results as interactive dataframes
- 📥 **Export Data** - Download tables as CSV

## Quick Start

```bash
# 1. Install Streamlit (if not already installed)
pip install streamlit

# 2. Run the app
./run_streamlit.sh

# Or manually:
streamlit run streamlit_app.py
```

The app will open at **http://localhost:8501**

## Usage Guide

### 1. Upload & Process Tab

1. **Upload PDF**: Click "Browse files" or drag & drop your PDF
2. **Click "Process PDF"**: Watch the progress as AI:
   - Chunks your document (512 tokens each)
   - Discovers data schemas (entities, attributes)
   - Extracts structured data into SQL tables
3. **View Results**: See chunks created, schemas discovered, entities extracted

**Example PDFs to try:**
- Annual reports (financial metrics)
- Contracts (parties, terms, dates)
- Invoices (vendors, amounts)
- Research papers (methods, results)

### 2. Chat & Query Tab

**Natural language interface** - just ask questions!

**Example queries:**
- "What was the total revenue?"
- "Show me all business segments"
- "List the top 5 expenses"
- "Which quarter had highest profit?"
- "What are the key findings?"

**Features:**
- Chat history persists during session
- View generated SQL queries
- Results displayed as interactive tables
- Click example questions to get started

### 3. View Tables Tab

**Explore your database:**
- Select any table from dropdown
- View table schema (column names, types)
- Browse data with pagination
- Download tables as CSV
- See AI-generated schema descriptions

**System tables:**
- `chunks` - Original document chunks with embeddings
- `schema_registry` - Discovered schemas metadata
- **Custom tables** - One per discovered entity type

## Architecture

```
User Upload → Streamlit Frontend
                ↓
        StructRAG Pipeline
                ↓
    ┌──────────┴──────────┐
    │  Ingestion          │ (PDF → Chunks)
    │  Schema Discovery   │ (AI Analysis)
    │  Entity Extraction  │ (SQL Tables)
    │  Query Engine       │ (NL → SQL)
    └──────────┬──────────┘
                ↓
        DuckDB Database
                ↓
    Interactive UI (Chat + Tables)
```

## Configuration

Edit `.env` to customize:

```bash
# Required
GROQ_API_KEY=gsk_YOUR_KEY_HERE

# Optional (defaults shown)
GROQ_MODEL=llama-3.3-70b-versatile
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

## Session Management

- **Database**: Each uploaded PDF creates a new database file
- **Chat history**: Persists during session
- **Reset**: Click "Start New Session" in sidebar to reset
- **Files**: Database files saved as `streamlit_db_<filename>.db`

## Performance

**Tested with 15MB PDF:**
- Upload: Instant
- Processing: 30-40 seconds
- Schema discovery: 1-2 seconds
- Queries: 500ms average

**Recommendations:**
- PDFs: < 50MB for best performance
- Groq free tier: 30 requests/min (enough for most workflows)
- First query slower (model loading), subsequent queries fast

## Advanced Features

### Custom SQL Queries

While in Chat tab, you can also execute raw SQL:

```sql
SELECT * FROM FinancialMetrics WHERE revenue > 1000000
```

The engine will detect SQL and execute directly.

### Multi-PDF Support

To analyze multiple PDFs:

1. Upload first PDF → Process → Query
2. Click "Start New Session" 
3. Upload second PDF → Process → Query

*Note: Cross-document queries coming in future version*

### Export Results

1. Ask a question in Chat tab
2. Results appear as dataframe
3. Or go to "View Tables" tab
4. Select table → Click "Download as CSV"

## Troubleshooting

**"GROQ_API_KEY not found"**
- Check `.env` file exists
- Verify key starts with `gsk_`
- Restart Streamlit app after editing .env

**"Error processing PDF"**
- Ensure PDF is not encrypted/password-protected
- Try smaller PDF (< 50MB)
- Check Groq API quota (free tier: 30 req/min)

**"No answer generated"**
- Question might be too vague
- Try more specific queries
- Check if schemas were discovered (sidebar metric)

**Slow processing**
- Large PDFs take longer (30-60s for 15MB)
- First run slower (model loading)
- Check internet connection (API calls to Groq)

## Demo Video Script

Perfect for recording demos:

### 1. Introduction (30 seconds)
- Show landing page
- Explain: "Transform PDFs into queryable databases with AI"

### 2. Upload & Process (1 minute)
- Upload sample PDF (annual report)
- Click "Process PDF"
- Show progress: chunking → schema discovery → extraction
- Highlight results: "42 chunks, 3 schemas, 15 entities"

### 3. Chat & Query (2 minutes)
- Ask: "What was the total revenue?"
- Show result table
- Ask: "Which business segment had highest profit?"
- Click "View SQL Query" to show translation
- Try 2-3 more questions

### 4. View Tables (1 minute)
- Switch to "View Tables" tab
- Select `FinancialMetrics` table
- Show schema details
- Browse data
- Click "Download CSV"

### 5. Conclusion (30 seconds)
- "Upload any PDF, discover structures, query naturally"
- Show GitHub link
- Call to action: "Try it yourself!"

## Technology Stack

- **Frontend**: Streamlit (Python web framework)
- **Backend**: StructRAG MCP pipeline
- **LLM**: Groq (llama-3.3-70b-versatile)
- **Database**: DuckDB (embedded SQL analytics)
- **Processing**: pypdf, semantic-text-splitter
- **UI Components**: Streamlit native (chat, dataframes, file upload)

## Future Enhancements

- [ ] Multi-PDF support (cross-document queries)
- [ ] Export to Excel/JSON
- [ ] Query history and saved queries
- [ ] Schema editing interface
- [ ] Batch PDF processing
- [ ] Authentication and user management
- [ ] Cloud deployment (Streamlit Cloud, AWS, GCP)
- [ ] API endpoint generation

## License

MIT License - Same as StructRAG MCP

---

**Built with ❤️ for easy document analysis**
