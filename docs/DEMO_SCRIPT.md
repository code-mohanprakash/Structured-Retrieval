# 🎬 Streamlit App Demo Script

Perfect script for recording your demo video!

## Setup (Before Recording)

1. Clean browser (clear cache, no extra tabs)
2. Have a test PDF ready (e.g., occidental_ars.pdf or any annual report)
3. Test run once to ensure everything works
4. Prepare talking points below

## Recording Script (5-minute demo)

### 🎬 Scene 1: Introduction (30 seconds)

**Screen:** Browser at http://localhost:8501  
**Show:** Landing page with title and tabs

**Say:**
> "Hi everyone! Today I'm showing you StructRAG - a tool that transforms any PDF into a queryable SQL database using AI. Unlike traditional document search, StructRAG discovers hidden data structures and lets you run analytics across your documents. Let me show you how it works."

---

### 🎬 Scene 2: Upload PDF (45 seconds)

**Screen:** Upload & Process tab  
**Action:** Click "Browse files" → Select PDF (or drag & drop)

**Say:**
> "First, I'll upload this annual report - it's a 15MB PDF with financial data, business segments, and executive information. I'll just drag it here... perfect. Now I click 'Process PDF' and watch what happens."

**Show:** 
- Progress bar moving through stages
- Status messages: "Ingesting PDF", "Discovering schemas", "Extracting entities"
- Final metrics: 42 chunks, 3 schemas, 15 entities

**Say:**
> "In about 30 seconds, the AI has chunked this entire document, discovered 3 data structures, and extracted entities into SQL tables. Notice it found FinancialMetrics, BusinessSegment, and CompanyInfo - all automatically!"

---

### 🎬 Scene 3: Chat & Query (2 minutes)

**Screen:** Switch to "Chat & Query" tab  
**Show:** Empty chat interface with example questions

**Say:**
> "Now I can ask questions in natural language. Let's try..."

**Query 1:** "What was the total revenue?"

**Action:** Type and send  
**Show:** 
- AI thinking animation
- Answer appears with data table
- Expand "View SQL Query" to show: `SELECT SUM(revenue) FROM FinancialMetrics`

**Say:**
> "It understood my question, converted it to SQL, and gave me the answer with the actual data. See how it generated this SQL query automatically? Let's try something more complex..."

**Query 2:** "Which business segment had the highest profit?"

**Action:** Type and send  
**Show:** 
- Results table with business segments ranked by profit
- SQL query shown

**Say:**
> "Perfect! It's ranking business segments by profit. This would be impossible with traditional keyword search - you need structured data and SQL for this kind of analysis."

**Query 3:** "Show me all acquisitions mentioned"

**Action:** Type and send  
**Show:** Table with acquisition data

**Say:**
> "And here it's pulling specific entities from the CompanyInfo table. The AI figured out where acquisition data lives and queried it directly."

---

### 🎬 Scene 4: View Tables (1 minute 30 seconds)

**Screen:** Switch to "View Tables" tab  
**Show:** Dropdown with table names

**Say:**
> "Let me show you what's happening under the hood. In the View Tables section, we can see all the tables that were created."

**Action:** Select "FinancialMetrics" from dropdown

**Show:**
- Table stats: 15 rows
- Expand "View Schema" - show columns and types
- Scroll through data
- Click "View Schema" section below

**Say:**
> "Here's the FinancialMetrics table with 15 rows of structured data. Look at this schema description - the AI wrote this based on analyzing the document. It identified columns for revenue, expenses, profit, quarter, and more. Let me download this..."

**Action:** Click "Download as CSV"

**Say:**
> "And just like that, I can export this to CSV for use in Excel or other tools."

**Action:** Switch to "BusinessSegment" table briefly

**Say:**
> "Same thing with BusinessSegment - clean structured data extracted from unstructured PDF."

---

### 🎬 Scene 5: Use Cases (45 seconds)

**Screen:** Switch back to Upload tab or show README on GitHub

**Say:**
> "So why is this powerful? Imagine you have 100 quarterly reports and you want to compare revenue trends across companies. Or 50 contracts and you need to find all clauses mentioning payment terms. Traditional search can't do this - you need structured data and SQL.

> With StructRAG, you upload your documents, the AI discovers the patterns, and you query them like a database. Finance, legal, research, procurement - any industry with lots of documents."

---

### 🎬 Scene 6: Conclusion & CTA (30 seconds)

**Screen:** Show GitHub page

**Say:**
> "This is all open source. The link is in the description - you can clone it, run it locally, and start analyzing your own documents in minutes. You just need a free Groq API key.

> I'd love to hear what you think - drop a comment or open an issue on GitHub if you have questions. Thanks for watching, and happy document analysis!"

---

## Technical Setup Notes

### Before Recording:
```bash
# 1. Start fresh session
rm -f streamlit_db_*.db

# 2. Run streamlit
./run_streamlit.sh

# 3. Test everything once
# 4. Clear browser cache
# 5. Restart streamlit for clean recording
```

### During Recording:
- **Screen resolution**: 1920x1080 (full HD)
- **Browser zoom**: 100% (default)
- **Hide bookmarks bar**: Cleaner look
- **Close unnecessary tabs**: Only StructRAG tab open
- **Terminal**: Hidden or in background

### Recording Tools:
- **macOS**: QuickTime Screen Recording or OBS
- **Windows**: OBS Studio or Camtasia
- **Linux**: OBS Studio or SimpleScreenRecorder

**Audio tips:**
- Use external mic if possible
- Quiet room (no background noise)
- Speak clearly and not too fast
- Pause between sections for easier editing

---

## Video Description Template

```
🚀 StructRAG: Transform PDFs into Queryable SQL Databases with AI

In this demo, I show how StructRAG automatically:
✅ Discovers data structures in your PDFs
✅ Extracts entities into SQL tables
✅ Lets you query with natural language
✅ Exports structured data as CSV

Perfect for:
📊 Financial analysis (quarterly reports, metrics)
📜 Legal contracts (clauses, terms, obligations)
🧾 Invoice processing (vendors, amounts, dates)
📰 Research papers (methods, results, citations)

🔗 GitHub: https://github.com/code-mohanprakash/Structured-Retrieval
📖 Docs: Full installation guide in README
🆓 Free to use (MIT License)

Tech Stack:
• Groq AI (llama-3.3-70b-versatile)
• DuckDB (embedded SQL database)
• Streamlit (web interface)
• Model Context Protocol (MCP)

⏱️ Timestamps:
0:00 - Introduction
0:30 - Upload & Process PDF
1:15 - Natural Language Queries
3:15 - View Tables & Export Data
4:45 - Use Cases & Wrap-up

💬 Questions? Drop a comment or open an issue on GitHub!

#AI #MachineLearning #RAG #StructuredData #DocumentAnalysis #Python #OpenSource #LLM #Groq #DataScience
```

---

## Thumbnail Ideas

### Option 1: Before/After
```
LEFT SIDE:                    RIGHT SIDE:
📄 Messy PDF               →  📊 Clean SQL Table
(blurred document)             (neat data table)

Text overlay: "PDF to SQL in 30 seconds"
```

### Option 2: Chat Interface
```
Screenshot of chat with question:
"What was the total revenue?"

With arrow pointing to result table

Text overlay: "Query PDFs Like Databases"
```

### Option 3: Split Screen
```
TOP: PDF preview
BOTTOM: Generated SQL tables

Text overlay: "AI Discovers Hidden Structure"
Badge: "Open Source"
```

### Design Tips:
- **Colors**: Blue (#4A90E2) for tech, green (#7CB342) for success
- **Font**: Bold, sans-serif (Montserrat or Roboto)
- **Size**: 1280x720 (HD standard for YouTube)
- **Tools**: Canva, Figma, or Photoshop

---

## Social Media Posts

### Twitter/X:
```
🚀 Just built StructRAG: Transform ANY PDF into a queryable SQL database using AI

Upload → AI discovers schemas → Query with natural language

Perfect for financial reports, contracts, research papers...

Free & open source! 🎉

Demo video: [link]
GitHub: [link]

#AI #MachineLearning #RAG
```

### LinkedIn:
```
Excited to share StructRAG - an open-source tool that transforms unstructured documents into structured SQL databases!

Unlike traditional document search, StructRAG:
✅ Discovers hidden data patterns using AI
✅ Extracts entities into queryable tables
✅ Enables analytics across thousands of documents

Built with: Groq AI • DuckDB • Streamlit • Model Context Protocol

Perfect for:
• Financial analysis (quarterly reports, metrics)
• Legal operations (contracts, compliance)
• Research (literature review, citation analysis)
• Business intelligence (invoices, procurement)

Demo video and full code on GitHub (link in comments).

Would love to hear your thoughts! What documents would you analyze?

#MachineLearning #AI #DocumentAnalysis #OpenSource #DataScience
```

### Reddit (r/MachineLearning, r/Python):
```
[P] StructRAG: Open-source PDF to SQL with AI schema discovery

Built a tool that transforms PDFs into queryable databases:
- Upload any document (reports, contracts, papers)
- AI discovers data structures automatically
- Query with natural language (converts to SQL)
- Web UI with Streamlit

Different from traditional RAG - focuses on structured extraction and analytics across documents, not just text retrieval.

Tech: Groq (llama-3.3-70b), DuckDB, MCP protocol
License: MIT

Demo: [video link]
Code: [GitHub link]

Feedback welcome! What features would make this more useful?
```

---

## Post-Production Checklist

- [ ] Add intro animation (3 seconds)
- [ ] Background music (subtle, non-distracting)
- [ ] Captions/subtitles (for accessibility)
- [ ] Speed up slow parts (2x during processing waits)
- [ ] Zoom in on important UI elements
- [ ] Add text overlays for key points
- [ ] End screen with links (20 seconds)
- [ ] Test audio levels (normalize)
- [ ] Export at 1080p 60fps
- [ ] Upload unlisted first, test playback

---

**Good luck with your demo! 🎬**
