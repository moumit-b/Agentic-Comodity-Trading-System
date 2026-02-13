"""Quick test to diagnose agent failures."""
import sys
import asyncio
sys.path.insert(0, r'C:\Users\moumi\Agentic-Comodotity-Trading-System\pharma-research-groq')

import config
from utils.llm_factory import get_llm
from agents.orchestrator_agent import OrchestratorAgent
from datetime import datetime

print("=" * 80)
print("SIMPLE AGENT DIAGNOSTIC TEST")
print("=" * 80)

# Initialize
print(f"\n[1/3] Initializing...")
print(f"Model: {config.GROQ_MODEL}")
print(f"Provider: {config.LLM_PROVIDER}")

try:
    llm = get_llm()
    orchestrator = OrchestratorAgent(None, None, llm)
    print(f"[OK] System initialized")
except Exception as e:
    print(f"[FAIL] Initialization error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Simple test query
test_query = "What is aspirin used for in medicine?"

print(f"\n[2/3] Processing simple query...")
print(f"Query: {test_query}")

session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

try:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    result = loop.run_until_complete(
        orchestrator.process_query(
            query=test_query,
            session_id=session_id,
            user_id="test_user"
        )
    )

    loop.close()

    print(f"\n[3/3] Results:")
    print(f"Complexity: {result.get('query_complexity')}")
    print(f"Agents assigned: {result.get('assigned_agents')}")
    print(f"Agent results count: {len(result.get('agent_results', []))}")

    # Check each agent result
    for agent_result in result.get('agent_results', []):
        print(f"\n{agent_result.agent_name}:")
        print(f"  Success: {agent_result.success}")
        if not agent_result.success:
            print(f"  ERROR: {agent_result.error_message}")
        else:
            answer = agent_result.result_data.get('answer', '')
            print(f"  Answer length: {len(answer)} chars")
            print(f"  Preview: {answer[:100]}...")

    # Final answer
    final_answer = result.get('final_answer', '')
    print(f"\nFinal Answer: {final_answer[:200]}...")

except Exception as e:
    print(f"\n[FAIL] Query processing error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("Diagnostic test complete")
print("=" * 80)
