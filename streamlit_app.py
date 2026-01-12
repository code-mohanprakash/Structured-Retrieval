"""
StructRAG MCP - Streamlit Web Interface

Upload PDFs, discover schemas, and query with natural language.
"""

import streamlit as st
import tempfile
import os
from pathlib import Path
import pandas as pd
import json
from structrag_mcp.storage import DuckDBManager, ProvenanceTracker
from structrag_mcp.ingestion import PDFParser, SemanticChunker, MetadataExtractor
from structrag_mcp.structure.schema_inductor import SchemaInductor
from structrag_mcp.structure.entity_extractor import EntityExtractor
from structrag_mcp.query.engine import QueryEngine
import duckdb

# Page config
st.set_page_config(
    page_title="StructRAG - PDF to SQL",
    page_icon="📄",
    layout="wide"
)

# Initialize session state
if 'db_path' not in st.session_state:
    st.session_state.db_path = None
if 'schemas_discovered' not in st.session_state:
    st.session_state.schemas_discovered = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'processing' not in st.session_state:
    st.session_state.processing = False

# Title and description
st.title("📄 StructRAG - Transform PDFs into Queryable Databases")
st.markdown("""
Upload a PDF → AI discovers data structures → Query with natural language
""")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Check for API key
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        st.success("✅ Groq API Key configured")
    else:
        st.error("❌ GROQ_API_KEY not found in .env")
        st.stop()
    
    st.markdown("---")
    
    # Database status
    st.header("📊 Database Status")
    if st.session_state.db_path:
        st.info(f"Active database: {Path(st.session_state.db_path).name}")
        
        # Show stats
        try:
            db = DuckDBManager(st.session_state.db_path)
            conn = db.conn
            
            chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            st.metric("Chunks", chunk_count)
            
            if st.session_state.schemas_discovered:
                schema_count = conn.execute("SELECT COUNT(DISTINCT entity_type) FROM schema_registry").fetchone()[0]
                st.metric("Schemas", schema_count)
        except Exception as e:
            st.warning(f"Could not load stats: {str(e)}")
    else:
        st.warning("No database active")
    
    st.markdown("---")
    
    # Reset button
    if st.button("🔄 Start New Session", use_container_width=True):
        st.session_state.db_path = None
        st.session_state.schemas_discovered = False
        st.session_state.chat_history = []
        st.rerun()

# Main content area with tabs
tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "💬 Chat & Query", "🗂️ View Tables"])

# ==================== TAB 1: Upload & Process ====================
with tab1:
    st.header("Upload Your PDF")
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Upload annual reports, contracts, invoices, or any structured document"
    )
    
    if uploaded_file:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.success(f"📄 {uploaded_file.name} ({uploaded_file.size / 1024 / 1024:.1f} MB)")
        
        with col2:
            process_btn = st.button("🚀 Process PDF", use_container_width=True, type="primary")
        
        if process_btn and not st.session_state.processing:
            st.session_state.processing = True
            
            # Create progress container
            progress_container = st.container()
            
            with progress_container:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                try:
                    # Step 1: Save uploaded file
                    status_text.text("📁 Saving PDF...")
                    progress_bar.progress(10)
                    
                    # Create temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                        tmp_file.write(uploaded_file.read())
                        pdf_path = tmp_file.name
                    
                    # Create database with timestamp to avoid conflicts
                    import time
                    db_name = uploaded_file.name.replace('.pdf', '').replace(' ', '_')
                    db_path = f"streamlit_db_{db_name}_{int(time.time())}.db"
                    st.session_state.db_path = db_path
                    
                    # Initialize database
                    db = DuckDBManager(db_path)
                    provenance = ProvenanceTracker(db)
                    
                    # Step 2: Parse PDF
                    status_text.text("📖 Parsing PDF...")
                    progress_bar.progress(20)
                    
                    parser = PDFParser()
                    parsed = parser.parse(pdf_path)
                    
                    # Extract metadata
                    metadata_extractor = MetadataExtractor()
                    file_metadata = metadata_extractor.extract_file_metadata(pdf_path)
                    metadata = {**parsed.get("metadata", {}), **file_metadata}
                    
                    # Insert document
                    doc_id = provenance.generate_doc_id(uploaded_file.name, pdf_path)
                    db.insert_document(doc_id, uploaded_file.name, pdf_path, ".pdf", metadata)
                    
                    # Step 3: Chunk document
                    status_text.text("✂️ Chunking document...")
                    progress_bar.progress(30)
                    
                    chunker = SemanticChunker()
                    chunks = chunker.chunk(parsed["text"], metadata)
                    
                    # Insert chunks
                    chunk_data = []
                    for i, chunk in enumerate(chunks):
                        chunk_id = provenance.generate_chunk_id(doc_id, i)
                        chunk_data.append({
                            "chunk_id": chunk_id,
                            "doc_id": doc_id,
                            "chunk_index": i,
                            "text": chunk["text"],
                            "token_count": chunk["token_count"],
                            "metadata": chunk.get("metadata", {})
                        })
                    
                    db.insert_chunks(chunk_data)
                    total_tokens = sum(c['token_count'] for c in chunks)
                    
                    progress_bar.progress(40)
                    status_text.text(f"✅ Ingested {len(chunks)} chunks, {total_tokens:,} tokens")
                    
                    # Step 4: Discover schemas
                    status_text.text("🔍 Discovering schemas (AI analyzing patterns)...")
                    progress_bar.progress(50)
                    
                    inductor = SchemaInductor(db)
                    schema_result = inductor.induce_schema(
                        entity_hints=["FinancialMetrics", "BusinessSegment", "CompanyInfo", "KeyPerson", "Event"]
                    )
                    
                    schemas = schema_result.entities
                    
                    progress_bar.progress(70)
                    status_text.text(f"✅ Discovered {len(schemas)} schemas")
                    
                    # Step 5: Extract entities
                    status_text.text("⚡ Extracting entities (populating tables)...")
                    progress_bar.progress(75)
                    
                    extractor = EntityExtractor(db, provenance)
                    total_entities = 0
                    for schema in schemas:
                        extraction_result = extractor.extract_entities(schema, document_id=doc_id)
                        total_entities += extraction_result.total_entities_found
                    
                    progress_bar.progress(100)
                    status_text.text("✅ Processing complete!")
                    
                    st.session_state.schemas_discovered = True
                    st.session_state.processing = False
                    
                    # Show results
                    st.success("🎉 PDF processed successfully!")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Chunks Created", len(chunks))
                    with col2:
                        st.metric("Schemas Discovered", len(schemas))
                    with col3:
                        st.metric("Entities Extracted", total_entities)
                    
                    # Show discovered schemas
                    st.subheader("📋 Discovered Schemas")
                    for schema in schemas:
                        with st.expander(f"🗂️ {schema.name}"):
                            st.markdown(f"**Entity:** {schema.name}")
                            st.markdown(f"**Table:** {schema.table_name or schema.name.lower()}")
                            st.markdown("**Attributes:**")
                            for attr in schema.attributes:
                                desc = f" - {attr.description}" if attr.description else ""
                                st.markdown(f"- `{attr.name}` ({attr.type}): confidence={attr.confidence}{desc}")
                    
                    # Clean up temp file
                    os.unlink(pdf_path)
                    
                    st.info("👉 Go to the 'Chat & Query' tab to start asking questions!")
                    
                except Exception as e:
                    st.error(f"❌ Error processing PDF: {str(e)}")
                    st.exception(e)
                    st.session_state.processing = False
    
    # Instructions when no file uploaded
    else:
        st.info("""
        ### 📝 How it works:
        
        1. **Upload** your PDF (annual report, contract, invoice, etc.)
        2. **AI discovers** hidden data structures automatically
        3. **Extract** structured data into SQL tables
        4. **Query** with natural language in the Chat tab
        
        ### ✨ Example Documents:
        - 📊 Financial reports (revenue, expenses, metrics)
        - 📜 Legal contracts (parties, terms, obligations)
        - 🧾 Invoices (vendors, amounts, dates)
        - 📰 Research papers (methodologies, results)
        """)

# ==================== TAB 2: Chat & Query ====================
with tab2:
    st.header("💬 Chat with Your Data")
    
    if not st.session_state.db_path or not st.session_state.schemas_discovered:
        st.warning("⚠️ Please upload and process a PDF first in the 'Upload & Process' tab")
    else:
        # Chat history display
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.chat_history:
                if message['role'] == 'user':
                    st.chat_message("user").write(message['content'])
                else:
                    with st.chat_message("assistant"):
                        st.write(message['content'])
                        if 'data' in message and message['data'] is not None:
                            st.dataframe(message['data'], use_container_width=True)
        
        # Query input
        query = st.chat_input("Ask a question about your document...")
        
        if query:
            # Add user message
            st.session_state.chat_history.append({
                'role': 'user',
                'content': query
            })
            
            # Show user message
            with chat_container:
                st.chat_message("user").write(query)
            
            # Process query
            try:
                with st.spinner("🤔 Thinking..."):
                    db = DuckDBManager(st.session_state.db_path)
                    engine = QueryEngine(db)
                    result = engine.query(query)
                
                # Format response
                response_text = result.get('answer', 'No answer generated')
                
                # Extract data if SQL was executed
                result_data = None
                if 'sql' in result and result['sql']:
                    try:
                        db = DuckDBManager(st.session_state.db_path)
                        conn = db.conn
                        df = conn.execute(result['sql']).fetchdf()
                        if not df.empty:
                            result_data = df
                    except Exception as e:
                        st.warning(f"Could not fetch data: {str(e)}")
                
                # Add assistant response
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': response_text,
                    'data': result_data
                })
                
                # Show assistant response
                with chat_container:
                    with st.chat_message("assistant"):
                        st.write(response_text)
                        if result_data is not None:
                            st.dataframe(result_data, use_container_width=True)
                        
                        # Show SQL in expander
                        if 'sql' in result and result['sql']:
                            with st.expander("🔍 View SQL Query"):
                                st.code(result['sql'], language='sql')
            
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                st.session_state.chat_history.append({
                    'role': 'assistant',
                    'content': error_msg
                })
                st.error(error_msg)
            
            st.rerun()
        
        # Example queries
        if len(st.session_state.chat_history) == 0:
            st.markdown("### 💡 Example Questions:")
            example_queries = [
                "What are the main topics covered in this document?",
                "Show me all the financial metrics",
                "What is the total revenue?",
                "List all entities mentioned",
                "What are the key findings?"
            ]
            
            cols = st.columns(2)
            for idx, example in enumerate(example_queries):
                with cols[idx % 2]:
                    if st.button(f"💬 {example}", key=f"example_{idx}", use_container_width=True):
                        st.session_state.chat_history.append({
                            'role': 'user',
                            'content': example
                        })
                        st.rerun()

# ==================== TAB 3: View Tables ====================
with tab3:
    st.header("🗂️ View Database Tables")
    
    if not st.session_state.db_path:
        st.warning("⚠️ Please upload and process a PDF first")
    else:
        try:
            db = DuckDBManager(st.session_state.db_path)
            conn = db.conn
            
            # Get all tables
            tables = conn.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'main'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """).fetchall()
            
            table_names = [t[0] for t in tables]
            
            # Table selector
            selected_table = st.selectbox(
                "Select a table to view:",
                table_names,
                help="Choose a table to see its contents"
            )
            
            if selected_table:
                # Get row count
                row_count = conn.execute(f"SELECT COUNT(*) FROM {selected_table}").fetchone()[0]
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(f"📊 {selected_table}")
                with col2:
                    st.metric("Rows", row_count)
                
                # Show table schema
                with st.expander("🔍 View Schema"):
                    schema_info = conn.execute(f"PRAGMA table_info({selected_table})").fetchdf()
                    st.dataframe(schema_info, use_container_width=True)
                
                # Show data with pagination
                page_size = st.slider("Rows per page", 10, 100, 50)
                
                df = conn.execute(f"SELECT * FROM {selected_table} LIMIT {page_size}").fetchdf()
                
                if not df.empty:
                    st.dataframe(df, use_container_width=True, height=400)
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name=f"{selected_table}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No data in this table")
                
                # Show discovered schemas if available
                if selected_table != 'chunks' and selected_table != 'schema_registry':
                    st.markdown("---")
                    st.subheader("📋 Schema Information")
                    
                    schema_info = conn.execute("""
                        SELECT entity_type, description, attributes, table_name
                        FROM schema_registry
                        WHERE table_name = ?
                    """, [selected_table]).fetchone()
                    
                    if schema_info:
                        st.markdown(f"**Entity Type:** {schema_info[0]}")
                        st.markdown(f"**Description:** {schema_info[1]}")
                        
                        import json
                        attributes = json.loads(schema_info[2])
                        st.markdown("**Attributes:**")
                        for attr in attributes:
                            st.markdown(f"- `{attr['name']}` ({attr['data_type']}): {attr['description']}")
        
        except Exception as e:
            st.error(f"Error loading tables: {str(e)}")
            st.exception(e)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    Built with StructRAG MCP • Powered by Groq AI • DuckDB
</div>
""", unsafe_allow_html=True)
