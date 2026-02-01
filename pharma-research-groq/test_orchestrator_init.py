"""Test orchestrator initialization to debug the UI issue."""
import sys
sys.path.insert(0, r'C:\Users\moumi\BU-Senior-Design-EMD-Serono\streamlit-app')

print("Testing Orchestrator initialization...")
print("="*70)

try:
    from utils.llm_factory import get_llm
    from agents.orchestrator_agent import OrchestratorAgent

    print("[1/2] Initializing LLM...")
    llm = get_llm()
    print(f"   LLM Type: {type(llm)}")
    print(f"   LLM Model: {llm.model_name if hasattr(llm, 'model_name') else 'Unknown'}")

    print("\n[2/2] Initializing Orchestrator...")
    orchestrator = OrchestratorAgent(
        mcp_orchestrator=None,
        governance_gateway=None,
        llm=llm
    )
    print(f"   Orchestrator Type: {type(orchestrator)}")
    print(f"   Orchestrator Agents: {list(orchestrator.agents.keys())}")

    print("\n" + "="*70)
    print("SUCCESS: Orchestrator initialized correctly!")
    print("="*70)

except Exception as e:
    print(f"\nERROR: {e}")
    print("\n" + "="*70)
    import traceback
    traceback.print_exc()
    print("="*70)
    sys.exit(1)
