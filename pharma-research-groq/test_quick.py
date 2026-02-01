"""Quick test to verify system is working."""
import sys
import asyncio
sys.path.insert(0, 'C:\\Users\\moumi\\BU-Senior-Design-EMD-Serono\\streamlit-app')

from agents.chemical_agent import ChemicalAgent
from agents.base_agent import AgentTask, AgentContext
from utils.llm_factory import get_llm
from reporting.report_generator import ReportGenerator
import time

print("=" * 60)
print("QUICK SYSTEM VERIFICATION TEST")
print("=" * 60)

# Test 1: LLM
print("\n[1/3] Testing Gemini 2.5 Flash...")
try:
    llm = get_llm()
    response = llm.invoke("What is water's formula?")
    answer = response.content if hasattr(response, 'content') else str(response)
    # Encode to handle special characters
    safe_answer = answer.encode('ascii', 'ignore').decode('ascii')
    print(f"   Query: What is water's formula?")
    print(f"   Answer: {safe_answer[:100]}...")
    print(f"   [OK] LLM working")
except Exception as e:
    print(f"   [FAIL] {e}")
    sys.exit(1)

# Test 2: Agent
print("\n[2/3] Testing ChemicalAgent...")

async def test_agent():
    class MockMCP:
        pass

    agent = ChemicalAgent(MockMCP(), llm)
    task = AgentTask(
        task_id="test1",
        query="What is the molecular formula of aspirin?",
        task_type="chem",
        session_id="test"
    )
    context = AgentContext(
        session_id="test",
        user_id="test-user",
        research_goal="Test"
    )
    result = await agent.process(task, context)
    return result

result = asyncio.run(test_agent())

if result.success and result.result_data.get("answer"):
    answer = result.result_data["answer"]
    safe_answer = answer.encode('ascii', 'ignore').decode('ascii')
    print(f"   Query: What is the molecular formula of aspirin?")
    print(f"   Answer: {safe_answer[:150]}...")
    print(f"   [OK] Agent working with LLM")
else:
    print(f"   [FAIL] Agent failed")
    sys.exit(1)

# Test 3: Report Generation
print("\n[3/3] Testing Report Generation...")

try:
    # Create mock session
    class MockQuery:
        def __init__(self, text):
            self.query_text = text
            self.agents_used = ["ChemicalAgent"]

    class MockEntity:
        def __init__(self, name):
            self.name = name

    class MockInsight:
        def __init__(self, content):
            self.content = content

    class MockSession:
        def __init__(self):
            self.session_id = "test-123"
            self.research_goal = "Test pharmaceutical research"
            self.queries = [MockQuery("What is aspirin?")]
            self.entities = [MockEntity("Aspirin"), MockEntity("NSAIDs")]
            self.insights = [MockInsight("Aspirin is an effective NSAID")]
            self.start_time = time.time()
            self.last_activity = time.time()

    class MockSessionManager:
        def __init__(self):
            self.session = MockSession()

        def get_session(self, sid):
            return self.session

    session_mgr = MockSessionManager()
    report_gen = ReportGenerator(session_mgr, llm)

    report = report_gen.generate_report("test-123")

    if report and len(report) > 200:
        print(f"   Report generated: {len(report)} characters")
        print(f"   Preview: {report[:200]}...")
        print(f"   [OK] Report generation working")

        # Save report
        with open("test_quick_report.md", "w", encoding="utf-8") as f:
            f.write(report)
        print(f"   Saved to: test_quick_report.md")
    else:
        print(f"   [FAIL] Report too short")
        sys.exit(1)

except Exception as e:
    print(f"   [FAIL] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("SUCCESS: All core components working!")
print("=" * 60)
print("\n System Status:")
print("  [OK] Gemini 2.5 Flash LLM")
print("  [OK] Specialized Agents (LLM-powered)")
print("  [OK] Report Generation (LLM sections)")
print("\nThe system is ready to use!")
print("Run: streamlit run app.py")
print("=" * 60)
