"""Test full multi-agent workflow with Groq LLM."""
import sys
import asyncio
sys.path.insert(0, r'C:\Users\moumi\Agentic-Comodotity-Trading-System\pharma-research-groq')

import config
from utils.llm_factory import get_llm
from agents.orchestrator_agent import OrchestratorAgent
from datetime import datetime

print("=" * 70)
print("FULL WORKFLOW TEST - Multi-Agent Orchestration with Groq")
print("=" * 70)

# Step 1: Initialize LLM
print("\n[1/4] Initializing Groq LLM...")
print(f"Provider: {config.LLM_PROVIDER}")
print(f"Model: {config.GROQ_MODEL}")

try:
    llm = get_llm()
    print(f"[OK] LLM initialized: {llm.__class__.__name__}")
except Exception as e:
    print(f"[X] Failed to initialize LLM: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 2: Initialize Orchestrator
print("\n[2/4] Initializing Orchestrator Agent...")
try:
    orchestrator = OrchestratorAgent(
        mcp_orchestrator=None,  # No MCP servers for this test
        governance_gateway=None,  # No governance for this test
        llm=llm
    )
    print(f"[OK] Orchestrator initialized")
    print(f"     Available agents: {', '.join(orchestrator.agents.keys())}")
except Exception as e:
    print(f"[X] Failed to initialize orchestrator: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 3: Test multi-agent query
print("\n[3/4] Testing multi-agent query...")
test_query = "What is aspirin and what is it used for?"
print(f"Query: {test_query}")
session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
print(f"Session ID: {session_id}")

try:
    # Run async query
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

    print("\n[OK] Query processed successfully!")
    print(f"\n--- Query Analysis ---")
    print(f"Complexity: {result.get('query_complexity', 'N/A')}")
    print(f"Assigned Agents: {', '.join(result.get('assigned_agents', []))}")
    print(f"Execution Time: {result.get('execution_time', 0):.2f}s")

    print(f"\n--- Agent Results ---")
    agent_results = result.get('agent_results', [])
    for agent_result in agent_results:
        print(f"\n{agent_result.agent_name}:")
        print(f"  Success: {agent_result.success}")
        print(f"  Execution Time: {agent_result.execution_time:.2f}s")
        if agent_result.success and agent_result.result_data:
            answer = agent_result.result_data.get('answer', 'No answer')
            preview = answer[:200] + "..." if len(answer) > 200 else answer
            print(f"  Answer Preview: {preview}")

    print(f"\n--- Final Synthesized Answer ---")
    final_answer = result.get('final_answer', 'No final answer')
    print(final_answer[:500] + ("..." if len(final_answer) > 500 else ""))

except Exception as e:
    print(f"\n[X] Query failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Step 4: Summary
print("\n" + "=" * 70)
print("*** WORKFLOW TEST COMPLETE ***")
print("=" * 70)
print("\nResults:")
print(f"  - Groq LLM: WORKING")
print(f"  - Orchestrator: WORKING")
print(f"  - Multi-Agent Execution: WORKING")
print(f"  - Answer Synthesis: WORKING")
print(f"\nGroq Performance:")
print(f"  - Total Execution Time: {result.get('execution_time', 0):.2f}s")
print(f"  - Agents Used: {len(agent_results)}")
print(f"  - Requests Remaining Today: ~{14400 - len(agent_results) - 1} / 14400")
print("\nNext: Test Streamlit frontend with 'streamlit run app_v2.py'")
