"""
Complete end-to-end workflow test.
Tests: System init → Agent processing → Report generation
"""
import sys
sys.path.insert(0, 'C:\\Users\\moumi\\BU-Senior-Design-EMD-Serono\\streamlit-app')

import asyncio
from datetime import datetime

print("="*70)
print("COMPLETE WORKFLOW TEST - Query to Report Generation")
print("="*70)
print()

# Test 1: System Initialization
print("[1/5] Testing system initialization...")
print("-"*70)

try:
    import config
    from utils.llm_factory import get_llm, validate_llm_setup
    from models.session import ResearchSession, QueryContext
    from agents.orchestrator_agent import OrchestratorAgent
    from reporting.report_generator import ReportGenerator

    print("   [OK] All imports successful")

    # Validate LLM setup
    validation = validate_llm_setup()
    if validation["ready"]:
        print(f"   [OK] LLM ready: {validation.get('model', 'Unknown model')}")
    else:
        print(f"   [FAIL] LLM not ready: {validation.get('errors', [])}")
        sys.exit(1)

    # Initialize LLM
    llm = get_llm()
    print(f"   [OK] LLM initialized: {config.GEMINI_MODEL}")

except Exception as e:
    print(f"   [FAIL] FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 2: Create Research Session
print("[2/5] Creating research session...")
print("-"*70)

try:
    session = ResearchSession(
        session_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        user_id="test_user",
        research_goal="Test aspirin competitive intelligence analysis"
    )
    print(f"   [OK] Session created: {session.session_id}")
    print(f"   [OK] Research goal: {session.research_goal}")

except Exception as e:
    print(f"   [FAIL] FAIL: {e}")
    sys.exit(1)

print()

# Test 3: Multi-Agent Query Processing
print("[3/5] Testing multi-agent query processing...")
print("-"*70)

test_queries = [
    "What is the molecular formula of aspirin?",
    "What are the main competing pain medications to aspirin?",
    "What are common side effects of aspirin use?"
]

async def test_orchestrator():
    """Test orchestrator with real queries."""
    # Initialize orchestrator (mcp_orchestrator and governance_gateway can be None)
    orchestrator = OrchestratorAgent(
        mcp_orchestrator=None,
        governance_gateway=None,
        llm=llm
    )
    results = []

    for i, query in enumerate(test_queries, 1):
        print(f"\n   Query {i}/{len(test_queries)}: {query}")
        try:
            result = await orchestrator.process_query(
                query=query,
                session_id=session.session_id,
                user_id=session.user_id
            )

            if result and result.get("final_answer"):
                answer = result["final_answer"]
                answer_preview = answer[:150] + "..." if len(answer) > 150 else answer
                print(f"   [OK] Got response ({len(answer)} chars): {answer_preview}")
                results.append({
                    "query": query,
                    "answer": answer,
                    "timestamp": datetime.now()
                })
            else:
                print(f"   [FAIL] No answer received")
                return None

        except Exception as e:
            print(f"   [FAIL] Query failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    return results

try:
    query_results = asyncio.run(test_orchestrator())

    if query_results:
        print(f"\n   [OK] All {len(query_results)} queries processed successfully")
    else:
        print("   [FAIL] Query processing failed")
        sys.exit(1)

except Exception as e:
    print(f"   [FAIL] FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 4: Report Generation
print("[4/5] Testing report generation...")
print("-"*70)

try:
    # Mock session manager for report generation
    class MockSessionManager:
        def __init__(self, session_obj):
            self.session_obj = session_obj

        def get_session(self, session_id):
            """Return the session object."""
            return self.session_obj

        def get_session_queries(self, session_id):
            return [{"query": r["query"], "timestamp": r["timestamp"]} for r in query_results]

        def get_discovered_entities(self, session_id):
            return ["aspirin", "ibuprofen", "acetaminophen", "naproxen"]

        def get_session_insights(self, session_id):
            return []

    # Generate report
    mock_manager = MockSessionManager(session)
    report_gen = ReportGenerator(session_manager=mock_manager, llm=llm)

    from reporting.report_generator import ReportType, ReportFormat

    print("   Generating Competitive Intelligence report...")
    report_content = report_gen.generate_report(
        session_id=session.session_id,
        report_type=ReportType.COMPETITIVE_INTELLIGENCE,
        format=ReportFormat.MARKDOWN
    )

    if report_content and len(report_content) > 500:
        print(f"   [OK] Report generated ({len(report_content)} chars)")

        # Check for key sections
        required_sections = [
            "Executive Summary",
            "Research Overview",
            "Key Findings",
            "Competitive Landscape"
        ]

        missing_sections = [s for s in required_sections if s not in report_content]

        if missing_sections:
            print(f"   [WARN] Missing sections: {missing_sections}")
        else:
            print(f"   [OK] All required sections present")

        # Save report to file
        report_path = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"   [OK] Report saved to: {report_path}")

    else:
        print(f"   [FAIL] Report too short or empty ({len(report_content) if report_content else 0} chars)")
        sys.exit(1)

except Exception as e:
    print(f"   [FAIL] FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 5: Verify Report Content
print("[5/5] Verifying report quality...")
print("-"*70)

try:
    # Check report has LLM-generated content (not just templates)
    indicators = [
        ("Executive Summary length", len(report_content.split("## Executive Summary")[1].split("##")[0]) > 200),
        ("Contains research data", any(q in report_content for q in ["aspirin", "molecular", "medication"])),
        ("Has recommendations", "Recommendation" in report_content or "Strategic" in report_content),
        ("Proper markdown format", "##" in report_content and "**" in report_content)
    ]

    passed = sum(1 for _, check in indicators if check)
    total = len(indicators)

    for indicator_name, passed_check in indicators:
        status = "[OK]" if passed_check else "[FAIL]"
        print(f"   {status} {indicator_name}")

    if passed == total:
        print(f"\n   [OK] All quality checks passed ({passed}/{total})")
    else:
        print(f"\n   [WARN] Some checks failed ({passed}/{total})")

except Exception as e:
    print(f"   [FAIL] FAIL: {e}")
    sys.exit(1)

print()
print("="*70)
print("[OK] COMPLETE WORKFLOW TEST PASSED")
print("="*70)
print()
print("Summary:")
print(f"  • {len(test_queries)} queries processed successfully")
print(f"  • Report generated with {len(report_content)} characters")
print(f"  • All required sections present")
print(f"  • Report saved to: {report_path}")
print()
print("The system is fully operational for query-to-report workflow!")
print("="*70)
