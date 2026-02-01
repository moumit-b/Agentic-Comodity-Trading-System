"""
Test that app_v2.py can process queries correctly.
Simulates what happens when a user asks a question in the UI.
"""
import sys
sys.path.insert(0, 'C:\\Users\\moumi\\BU-Senior-Design-EMD-Serono\\streamlit-app')

import asyncio
import config
from utils.llm_factory import get_llm, validate_llm_setup
from agents.orchestrator_agent import OrchestratorAgent

print("="*70)
print("APP QUERY TEST - Simulating Streamlit App Query Processing")
print("="*70)
print()

# Test 1: Validate LLM (same as app does)
print("[1/3] Validating LLM setup...")
validation = validate_llm_setup()
print(f"   LLM Ready: {validation['ready']}")
print(f"   Model: {validation.get('model', 'N/A')}")
print()

# Test 2: Initialize Orchestrator (same as app does)
print("[2/3] Initializing orchestrator...")
try:
    llm = get_llm()
    orchestrator = OrchestratorAgent(
        mcp_orchestrator=None,
        governance_gateway=None,
        llm=llm
    )
    print("   [OK] Orchestrator initialized successfully")
except Exception as e:
    print(f"   [FAIL] Orchestrator initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 3: Process a query (same as app does)
print("[3/3] Processing test query...")
test_query = "What is aspirin?"
session_id = "test_session"
user_id = "test_user"

async def process_query():
    """Process query exactly like the app does."""
    try:
        result = await orchestrator.process_query(
            query=test_query,
            session_id=session_id,
            user_id=user_id
        )
        return result
    except Exception as e:
        print(f"   [FAIL] Query processing failed: {e}")
        import traceback
        traceback.print_exc()
        return None

# Run async query
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
result = loop.run_until_complete(process_query())
loop.close()

if result:
    print(f"   [OK] Query processed successfully")
    print(f"   Query: {test_query}")
    print(f"   Response length: {len(result.get('final_answer', ''))} chars")
    print(f"   Agents used: {', '.join(result.get('assigned_agents', []))}")
    print(f"   Execution time: {result.get('execution_time', 0):.2f}s")
    print()
    print("   Response preview:")
    preview = result.get('final_answer', '')[:200] + "..."
    print(f"   {preview}")
else:
    print("   [FAIL] No result returned")
    sys.exit(1)

print()
print("="*70)
print("[OK] APP QUERY TEST PASSED")
print("="*70)
print()
print("The app should now be able to process queries!")
print("Start the app with: streamlit run app_v2.py")
