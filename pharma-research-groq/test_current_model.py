"""Test if current model has quota available."""
import sys
sys.path.insert(0, r'C:\Users\moumi\BU-Senior-Design-EMD-Serono\streamlit-app')

import config
from utils.llm_factory import get_llm

print("="*70)
print(f"Testing Model: {config.GEMINI_MODEL}")
print("="*70)

try:
    llm = get_llm()

    print("\nSending test query to LLM...")
    response = llm.invoke("Say 'I am working' in one sentence.")
    answer = response.content if hasattr(response, 'content') else str(response)

    print(f"\nRESPONSE: {answer}")
    print("\n" + "="*70)
    print(f"SUCCESS: {config.GEMINI_MODEL} has quota available!")
    print("="*70)

except Exception as e:
    error_msg = str(e)
    print(f"\nERROR: {error_msg}")

    if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
        print("\n" + "="*70)
        print("QUOTA EXHAUSTED - Need to switch models")
        print("="*70)

        # Extract retry time if available
        if "retry" in error_msg.lower():
            import re
            match = re.search(r'(\d+\.?\d*)\s*s', error_msg)
            if match:
                print(f"\nRetry in: {match.group(1)} seconds")
    else:
        print("\n" + "="*70)
        print("UNEXPECTED ERROR")
        print("="*70)
        import traceback
        traceback.print_exc()
