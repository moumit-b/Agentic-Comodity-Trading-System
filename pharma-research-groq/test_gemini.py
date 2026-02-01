"""Quick test script to verify Gemini connection with new model."""
import sys
sys.path.insert(0, 'C:\\Users\\moumi\\BU-Senior-Design-EMD-Serono\\streamlit-app')

from utils.llm_factory import get_llm, validate_llm_setup

print("=" * 60)
print("Testing Gemini Connection")
print("=" * 60)

# Validate LLM setup
print("\n1. Validating LLM setup...")
validation = validate_llm_setup()
print(f"   Ready: {validation['ready']}")
print(f"   Model: {validation.get('model', 'N/A')}")
if not validation['ready']:
    print(f"   Errors: {validation.get('errors', [])}")
    sys.exit(1)

# Test LLM initialization
print("\n2. Initializing LLM...")
try:
    llm = get_llm()
    print(f"   [OK] LLM initialized successfully")
except Exception as e:
    print(f"   [FAIL] Failed: {e}")
    sys.exit(1)

# Test simple query
print("\n3. Testing simple query...")
try:
    response = llm.invoke("What is the molecular formula of water? Answer in one sentence.")
    answer = response.content if hasattr(response, 'content') else str(response)
    print(f"   Query: 'What is the molecular formula of water?'")
    print(f"   Response: {answer[:200]}")
    print(f"   [OK] Query successful")
except Exception as e:
    print(f"   [FAIL] Query failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("[SUCCESS] All tests passed! Gemini 2.5 Flash is working correctly.")
print("=" * 60)
