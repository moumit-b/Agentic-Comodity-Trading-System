"""Test Groq API connection and basic functionality."""
import sys
sys.path.insert(0, r'C:\Users\moumi\Agentic-Comodotity-Trading-System\pharma-research-groq')

import config
from utils.llm_factory import get_llm, validate_llm_setup

print("=" * 70)
print("GROQ API CONNECTION TEST")
print("=" * 70)

# Step 1: Validate configuration
print("\n[1/3] Validating LLM configuration...")
print(f"Provider: {config.LLM_PROVIDER}")
print(f"Model: {config.GROQ_MODEL}")

validation = validate_llm_setup()
print(f"\nValidation result: {validation}")

if not validation["ready"]:
    print("\n[X] LLM NOT READY")
    print("\nTo fix this:")
    print("1. Go to: https://console.groq.com/keys")
    print("2. Sign up for FREE (no credit card required)")
    print("3. Create an API key")
    print("4. Add it to .env file: GROQ_API_KEY=your-key-here")
    print("\nGroq offers 14,400 FREE requests per day (720x more than Gemini)!")
    sys.exit(1)

print("[OK] Configuration valid")

# Step 2: Initialize LLM
print("\n[2/3] Initializing Groq LLM...")
try:
    llm = get_llm()
    print(f"[OK] LLM initialized: {llm.__class__.__name__}")
except Exception as e:
    print(f"[X] Failed to initialize LLM: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Test simple query
print("\n[3/3] Testing simple query...")
try:
    test_query = "Say 'Groq is working!' in one sentence."
    print(f"Query: {test_query}")

    response = llm.invoke(test_query)
    answer = response.content if hasattr(response, 'content') else str(response)

    print(f"\nResponse: {answer}")
    print("\n" + "=" * 70)
    print("*** SUCCESS - Groq is fully operational! ***")
    print("=" * 70)
    print(f"\nYou now have {14400} FREE requests per day with Groq!")
    print("   (That's 720x more than Gemini's 20 requests/day)")

except Exception as e:
    print(f"\n[X] Query failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
