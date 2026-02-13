"""
Comprehensive multi-agent test to verify ALL agents are utilized.
This test uses a complex query designed to trigger all 5 specialized agents.
"""
import sys
import asyncio
sys.path.insert(0, r'C:\Users\moumi\Agentic-Comodotity-Trading-System\pharma-research-groq')

import config
from utils.llm_factory import get_llm
from agents.orchestrator_agent import OrchestratorAgent
from datetime import datetime

print("=" * 80)
print("COMPREHENSIVE MULTI-AGENT TEST - llama-3.3-70b-versatile")
print("=" * 80)

# Verify configuration
print(f"\n[CONFIG]")
print(f"  Provider: {config.LLM_PROVIDER}")
print(f"  Model: {config.GROQ_MODEL}")
print(f"  Expected: llama-3.3-70b-versatile")

if config.GROQ_MODEL != "llama-3.3-70b-versatile":
    print(f"\n  WARNING: Model is {config.GROQ_MODEL}, not llama-3.3-70b-versatile!")

# Initialize LLM
print(f"\n[1/4] Initializing LLM...")
try:
    llm = get_llm()
    print(f"  [OK] LLM initialized: {llm.__class__.__name__}")
    print(f"  [OK] Model: {config.GROQ_MODEL}")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Initialize Orchestrator
print(f"\n[2/4] Initializing Orchestrator...")
try:
    orchestrator = OrchestratorAgent(
        mcp_orchestrator=None,
        governance_gateway=None,
        llm=llm
    )
    print(f"  [OK] Orchestrator initialized")
    print(f"  [OK] Available agents: {', '.join(orchestrator.agents.keys())}")
    print(f"  [OK] Agent count: {len(orchestrator.agents)}")
except Exception as e:
    print(f"  [FAIL] Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Complex query designed to trigger ALL agents
test_query = """
Conduct a comprehensive analysis of metformin for treating type 2 diabetes:

1. CHEMICAL: Provide molecular structure, mechanism of action, and pharmacokinetics
2. CLINICAL: Summarize clinical trial data, FDA approval, dosing guidelines, and efficacy metrics
3. LITERATURE: Find key research papers and recent studies on metformin and diabetes
4. GENE: Analyze genetic factors (SLC22A1, SLC22A2 transporters, AMPK pathway)
5. DATA: Provide statistical analysis of treatment outcomes and comparative effectiveness

Synthesize findings into a comprehensive report suitable for clinical decision-making.
"""

print(f"\n[3/4] Testing Complex Multi-Agent Query...")
print(f"\nQuery (designed to trigger ALL 5 agents):")
print("-" * 80)
print(test_query.strip())
print("-" * 80)

session_id = f"test_multi_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
print(f"\nSession ID: {session_id}")

try:
    # Run async query
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    print(f"\n  Processing query (this may take 30-60 seconds with llama-3.3-70b)...")
    start_time = datetime.now()

    result = loop.run_until_complete(
        orchestrator.process_query(
            query=test_query,
            session_id=session_id,
            user_id="test_user"
        )
    )

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    loop.close()

    print(f"\n  [OK] Query completed in {elapsed:.2f}s")

except Exception as e:
    print(f"\n  [FAIL] Query failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Analyze results
print(f"\n[4/4] Analyzing Results...")
print("=" * 80)

# Query analysis
complexity = result.get('query_complexity', 'unknown')
assigned_agents = result.get('assigned_agents', [])
print(f"\nQuery Complexity: {complexity}")
print(f"Agents Assigned by Orchestrator: {', '.join(assigned_agents)}")
print(f"Number of Agents Assigned: {len(assigned_agents)}")

# Check if all agents were used
all_agent_names = ['chemical', 'clinical', 'literature', 'gene', 'data']
agents_used = set()
agent_results = result.get('agent_results', [])

print(f"\n--- Agent Execution Results ---")
for agent_result in agent_results:
    agent_name = agent_result.agent_name.lower().replace('agent', '')
    agents_used.add(agent_name)

    print(f"\n{agent_result.agent_name}:")
    print(f"  Success: {agent_result.success}")
    print(f"  Execution Time: {agent_result.execution_time:.2f}s")

    if agent_result.success and agent_result.result_data:
        answer = agent_result.result_data.get('answer', '')
        if answer:
            preview = answer[:300] + "..." if len(answer) > 300 else answer
            print(f"  Answer Preview: {preview}")
            print(f"  Answer Length: {len(answer)} chars")

# Verify all agents were used
print(f"\n--- Agent Coverage Analysis ---")
missing_agents = set(all_agent_names) - agents_used
if missing_agents:
    print(f"  [WARNING] Missing agents: {', '.join(missing_agents)}")
    print(f"  [WARNING] Only {len(agents_used)}/5 agents were used")
else:
    print(f"  [SUCCESS] All 5 agents were utilized!")
    print(f"  [OK] Agents used: {', '.join(sorted(agents_used))}")

# Final synthesis
final_answer = result.get('final_answer', '')
print(f"\n--- Final Synthesized Answer ---")
print(f"Length: {len(final_answer)} chars")
print(f"Preview (first 500 chars):")
print(final_answer[:500] + ("..." if len(final_answer) > 500 else ""))

# Performance summary
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print(f"Model: {config.GROQ_MODEL}")
print(f"Total Execution Time: {elapsed:.2f}s")
print(f"Agents Utilized: {len(agents_used)}/5")
print(f"Query Complexity: {complexity}")
print(f"Final Answer Length: {len(final_answer)} chars")

if len(agents_used) == 5:
    print(f"\n*** SUCCESS: All 5 agents were properly utilized!")
    print(f"    The orchestrator is working correctly.")
else:
    print(f"\n*** FAILURE: Only {len(agents_used)}/5 agents used")
    print(f"    Missing: {', '.join(missing_agents)}")
    print(f"    The orchestrator needs investigation.")
    sys.exit(1)

print(f"\nNext: Test report generation with 'test_report_generation.py'")
