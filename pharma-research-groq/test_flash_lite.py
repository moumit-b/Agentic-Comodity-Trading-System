"""Test gemini-2.5-flash-lite model."""
import sys
sys.path.insert(0, 'C:\\Users\\moumi\\BU-Senior-Design-EMD-Serono\\streamlit-app')

from utils.llm_factory import get_llm

print("Testing gemini-2.5-flash-lite...")

try:
    llm = get_llm()
    response = llm.invoke("Say 'Flash Lite is working' in one sentence.")
    answer = response.content if hasattr(response, 'content') else str(response)
    safe_answer = answer.encode('ascii', 'ignore').decode('ascii')
    print(f"Model: gemini-2.5-flash-lite")
    print(f"Response: {safe_answer}")
    print(f"\n[SUCCESS] gemini-2.5-flash-lite is working!")
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
