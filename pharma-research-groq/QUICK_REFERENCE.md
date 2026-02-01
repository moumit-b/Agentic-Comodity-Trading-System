# Quick Reference - Pharmaceutical Research Intelligence System

## ✅ System Status: FULLY OPERATIONAL

---

## 🚀 How to Start

### Run the Streamlit App
```bash
cd C:\Users\moumi\BU-Senior-Design-EMD-Serono\streamlit-app
streamlit run app_v2.py
```

**App will open at:** http://localhost:8502

---

## 💬 How to Use

### Ask Research Questions

Just type questions in the chat interface:

**Example Questions:**
- "What is the molecular formula of aspirin?"
- "What are the main competing NSAIDs?"
- "What are aspirin's side effects?"
- "How does ibuprofen compare to aspirin?"
- "What is the mechanism of action of statins?"
- "What are the latest clinical trials for metformin?"

### Expected Response

The system will:
1. Route your query to relevant specialized agents
2. Generate 5,000-12,000 character detailed responses
3. Synthesize findings from multiple agents
4. Provide comprehensive pharmaceutical research intelligence

---

## 📊 Generate Reports

### Programmatic Report Generation

```python
from reporting import ReportGenerator, ReportType, ReportFormat

# After asking multiple research questions...
report_gen = ReportGenerator(session_manager=session_manager, llm=llm)

report = report_gen.generate_report(
    session_id="your_session_id",
    report_type=ReportType.COMPETITIVE_INTELLIGENCE,
    format=ReportFormat.MARKDOWN
)

# Save report
with open("my_report.md", "w") as f:
    f.write(report)
```

---

## 🧪 Verify System Health

### Test 1: LLM Connection
```bash
venv/Scripts/python.exe test_flash_lite.py
```
**Expected:** "Flash Lite is working!"

### Test 2: All Imports
```bash
venv/Scripts/python.exe test_app_v2_imports.py
```
**Expected:** "SUCCESS: All app_v2.py imports working!"

### Test 3: Full Workflow
```bash
venv/Scripts/python.exe test_full_workflow.py
```
**Expected:** "COMPLETE WORKFLOW TEST PASSED"

---

## ⚙️ What's Working

- ✅ **Gemini 2.5 Flash Lite** - Free tier LLM
- ✅ **5 Specialized Agents** - Chemical, Clinical, Literature, Gene, Data
- ✅ **Multi-Agent Orchestration** - LLM synthesis of findings
- ✅ **Report Generation** - Professional CI reports with LLM sections
- ✅ **Streamlit UI** - Interactive research interface

---

## ⚠️ Rate Limits

**Free Tier:** 20 requests per day

If you see:
```
Error: RESOURCE_EXHAUSTED
Quota exceeded... Please retry in 15s
```

**Options:**
1. Wait for quota reset (next day)
2. Upgrade to paid tier: https://aistudio.google.com

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `app_v2.py` | Main Streamlit application |
| `config.py` | Configuration (API keys, model settings) |
| `test_full_workflow.py` | End-to-end test script |
| `TESTING_COMPLETE.md` | Full testing documentation |
| `QUICK_REFERENCE.md` | This file |

---

## 🐛 Troubleshooting

### App won't start
```bash
# Kill any running Python processes
taskkill /F /IM python.exe

# Restart app
streamlit run app_v2.py
```

### LLM not working
Check `config.py` line 37:
```python
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyCR4oXUwMV8SUwh2UYC-ouh_0cN6LdRcZE"
```

### Import errors
```bash
# Reinstall dependencies
venv/Scripts/python.exe -m pip install langchain-google-genai markdown
```

---

## 📧 Support

**Documentation:**
- Full testing results: `TESTING_COMPLETE.md`
- Implementation summary: `IMPLEMENTATION_SUMMARY.md`
- Quick start guide: `QUICKSTART.md`

---

*Last Updated: 2026-01-30*
*Status: ✅ READY TO USE*
