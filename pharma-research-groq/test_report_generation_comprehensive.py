"""
Test comprehensive competitive intelligence report generation with llama-3.3-70b-versatile.
Tests the full workflow: query processing -> report generation.
"""
import sys
import asyncio
from datetime import datetime
sys.path.insert(0, r'C:\Users\moumi\Agentic-Comodotity-Trading-System\pharma-research-groq')

import config
from utils.llm_factory import get_llm
from agents.orchestrator_agent import OrchestratorAgent
from orchestration.session_manager import SessionManager
from reporting.report_generator import ReportGenerator, ReportType

print("=" * 80)
print("COMPETITIVE INTELLIGENCE REPORT TEST - llama-3.3-70b-versatile")
print("=" * 80)

# Verify model
print(f"\n[CONFIG]")
print(f"  Model: {config.GROQ_MODEL}")
print(f"  Provider: {config.LLM_PROVIDER}")

# Initialize components
print(f"\n[1/5] Initializing system components...")
try:
    llm = get_llm()
    orchestrator = OrchestratorAgent(None, None, llm)
    session_manager = SessionManager()
    report_generator = ReportGenerator(session_manager, llm)
    print(f"  [OK] All components initialized")
except Exception as e:
    print(f"  [FAIL] Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Create comprehensive test query for pharmaceutical research
test_query = """
Conduct a detailed competitive intelligence analysis on GLP-1 receptor agonists
for treating type 2 diabetes and obesity. Include:

1. Market landscape and key players (semaglutide, liraglutide, dulaglutide)
2. Clinical efficacy data and comparative effectiveness
3. Patent landscape and exclusivity periods
4. Recent literature and clinical trial results
5. Molecular mechanisms and pharmacological profiles
6. Genetic factors affecting response rates
7. Statistical analysis of treatment outcomes
8. Competitive advantages and disadvantages
9. Market opportunities and threats
10. Strategic recommendations for market positioning
"""

print(f"\n[2/5] Creating research session...")
session = session_manager.create_session(
    user_id="test_user",
    research_goal="Competitive Intelligence: GLP-1 Receptor Agonists Market Analysis"
)
session_id = session.session_id
print(f"  [OK] Session created: {session_id}")

print(f"\n[3/5] Processing comprehensive research query...")
print(f"  (This may take 60-90 seconds with llama-3.3-70b for thorough analysis)")

try:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

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

    print(f"  [OK] Query processed in {elapsed:.2f}s")
    print(f"  Agents used: {', '.join(result.get('assigned_agents', []))}")
    print(f"  Answer length: {len(result.get('final_answer', ''))} chars")

except Exception as e:
    print(f"  [FAIL] Query processing failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n[4/5] Generating Competitive Intelligence Report...")
print(f"  Using llama-3.3-70b for rich reasoning and synthesis...")

try:
    start_time = datetime.now()

    report_content = report_generator.generate_report(
        session_id=session_id,
        report_type=ReportType.COMPETITIVE_INTELLIGENCE
    )

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    print(f"  [OK] Report generated in {elapsed:.2f}s")
    print(f"  Report length: {len(report_content)} chars")

except Exception as e:
    print(f"  [FAIL] Report generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\n[5/5] Analyzing Report Quality...")

# Save report
report_path = f"test_report_groq_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(report_content)

print(f"  [OK] Report saved to: {report_path}")

# Analyze report sections
sections = {
    "Executive Summary": "## Executive Summary" in report_content,
    "Research Overview": "## Research Overview" in report_content,
    "Key Findings": "## Key Findings" in report_content,
    "Entities Discovered": "## Entities Discovered" in report_content,
    "Competitive Landscape": "## Competitive Landscape" in report_content,
    "Recommendations": "## Recommendations" in report_content
}

print(f"\n  Report Sections Present:")
for section, present in sections.items():
    status = "[OK]" if present else "[MISSING]"
    print(f"    {status} {section}")

# Quality metrics
quality_metrics = {
    "Length": len(report_content),
    "Has structure": report_content.count("##") >= 5,
    "Has data": "Total Queries" in report_content,
    "Comprehensive": len(report_content) > 2000,
}

print(f"\n  Quality Metrics:")
for metric, value in quality_metrics.items():
    print(f"    {metric}: {value}")

# Show report preview
print(f"\n--- Report Preview (first 1000 chars) ---")
print(report_content[:1000])
print(f"...")

print("\n" + "=" * 80)
print("REPORT GENERATION TEST SUMMARY")
print("=" * 80)
print(f"Model: {config.GROQ_MODEL}")
print(f"Query Processing Time: {elapsed:.2f}s (multi-agent orchestration)")
print(f"Report Generation Time: {elapsed:.2f}s (LLM synthesis)")
print(f"Report Length: {len(report_content)} characters")
print(f"Sections Present: {sum(sections.values())}/{len(sections)}")
print(f"Report File: {report_path}")

if all(sections.values()) and len(report_content) > 2000:
    print(f"\n*** SUCCESS: Comprehensive report generated successfully!")
    print(f"    The llama-3.3-70b model provided rich, detailed analysis.")
else:
    print(f"\n*** WARNING: Report may be incomplete")
    print(f"    Missing sections: {[k for k, v in sections.items() if not v]}")

print(f"\nOpen {report_path} to review the full competitive intelligence report.")
