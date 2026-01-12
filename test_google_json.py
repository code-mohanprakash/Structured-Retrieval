"""
MINIMAL TEST: Test Google Gemini JSON response handling
This directly tests if our JSON parsing can handle Gemini's responses
"""

import os
import sys
from pathlib import Path

# Setup
sys.path.insert(0, str(Path(__file__).parent / 'src'))
os.chdir(Path(__file__).parent)

from structrag_mcp.llm.provider import complete_with_fallback

# Test prompt - same structure as schema induction
test_prompt = """
Analyze this text and extract entity schemas in JSON format:

Text: "Apple Inc. announced Q4 earnings of $90B. CEO Tim Cook stated revenue grew 15%."

Return JSON with this structure:
{
  "entities": [
    {
      "name": "Company",
      "attributes": [
        {"name": "name", "data_type": "TEXT", "confidence": 0.95},
        {"name": "revenue", "data_type": "DECIMAL", "confidence": 0.90}
      ]
    }
  ]
}
"""

print("=" * 60)
print("Testing Google Gemini JSON Response Handling")
print("=" * 60)

print("\n📤 Sending test prompt to Google Gemini...")
print(f"   Model: {os.getenv('GOOGLE_MODEL', 'gemini-2.5-flash')}")

response = complete_with_fallback(
    system_prompt="You are a data extraction expert. Always return valid JSON.",
    user_prompt=test_prompt,
    json_mode=True
)

print(f"\n📥 Response received:")
print(f"   Provider: {response.provider}")
print(f"   Model: {response.model}")
print(f"   Tokens: {response.total_tokens}")

if response.error:
    print(f"\n❌ ERROR: {response.error}")
    sys.exit(1)

print(f"\n📝 Raw response content:\n")
print("-" * 60)
print(response.content)
print("-" * 60)

# Test JSON parsing
print("\n🔍 Testing JSON parsing...")

try:
    import json
    
    # Try direct parse first
    try:
        data = json.loads(response.content)
        print("✅ Direct JSON parse: SUCCESS")
        print(f"   Structure: {list(data.keys())}")
    except json.JSONDecodeError as e:
        print(f"⚠️  Direct parse failed: {str(e)}")
        print("   Trying with markdown stripping...")
        
        # Try with our markdown stripper
        from structrag_mcp.structure.schema_inductor import _strip_markdown_json
        
        clean_content = _strip_markdown_json(response.content)
        print(f"\n   Cleaned content:\n{clean_content[:200]}...")
        
        data = json.loads(clean_content)
        print("\n✅ JSON parse with stripping: SUCCESS")
        print(f"   Structure: {list(data.keys())}")
    
    # Show parsed data
    if "entities" in data:
        print(f"\n✅ Found 'entities' key with {len(data['entities'])} items")
        for entity in data['entities']:
            print(f"   - {entity.get('name', 'Unknown')}: {len(entity.get('attributes', []))} attributes")
    else:
        print(f"\n⚠️  No 'entities' key found. Keys: {list(data.keys())}")
    
    print("\n" + "=" * 60)
    print("✅ TEST PASSED - JSON parsing works!")
    print("=" * 60)
    sys.exit(0)

except Exception as e:
    print(f"\n❌ JSON parsing FAILED: {str(e)}")
    print("\n" + "=" * 60)
    print("❌ TEST FAILED - JSON parsing broken")
    print("=" * 60)
    import traceback
    traceback.print_exc()
    sys.exit(1)
