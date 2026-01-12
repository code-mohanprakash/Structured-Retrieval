#!/bin/bash
# Quick start script for StructRAG Streamlit app

echo "🚀 Starting StructRAG Web Interface..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env and add your GROQ_API_KEY"
    echo "   Get a free key at: https://console.groq.com/keys"
    exit 1
fi

# Check if GROQ_API_KEY is set
if ! grep -q "GROQ_API_KEY=gsk_" .env; then
    echo "⚠️  GROQ_API_KEY not configured in .env"
    echo "   Get a free key at: https://console.groq.com/keys"
    exit 1
fi

# Install streamlit if not already installed
if ! pip show streamlit > /dev/null 2>&1; then
    echo "📦 Installing Streamlit..."
    pip install streamlit
    echo ""
fi

# Load .env and start streamlit
export $(cat .env | xargs)

echo "✅ Starting Streamlit app on http://localhost:8501"
echo ""
echo "📝 Upload a PDF, discover schemas, and query with natural language!"
echo ""

streamlit run streamlit_app.py
