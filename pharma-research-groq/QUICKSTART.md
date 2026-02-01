# Quick Start Guide - Pharmaceutical Research Intelligence System

## ✅ System is Ready!

The system has been fully implemented and tested. All agents are using Gemini 2.5 Flash and working correctly.

---

## 🚀 How to Start

### 1. Activate Virtual Environment

```bash
cd C:\Users\moumi\BU-Senior-Design-EMD-Serono\streamlit-app
venv\Scripts\activate
```

### 2. Run the Streamlit App

**For FULL functionality with report generation:**
```bash
streamlit run app_v2.py
```

**For simple chat interface:**
```bash
streamlit run app.py
```

The app will open in your browser at: `http://localhost:8501`

---

## 💬 How to Use

### 🚀 RECOMMENDED: Full System (app_v2.py)

**Complete workflow with report generation:**

1. **Start Session**
   - Click "Start New Session" in sidebar
   - Enter research goal (e.g., "Analyze aspirin market")

2. **Ask Research Questions**
   - Ask multiple queries in chat
   - Examples:
     - "What is the molecular formula of aspirin?"
     - "What are competing NSAIDs?"
     - "What are aspirin's side effects?"
     - "What is the market size for pain relievers?"

3. **Generate Full CI Report**
   - Click "Generate Report" button in sidebar
   - System creates comprehensive report with:
     - Executive Summary (LLM-generated)
     - Key Findings (LLM-generated)
     - Competitive Landscape (LLM-generated)
     - Strategic Recommendations (LLM-generated)

4. **Download Report**
   - Click "Download Report" to get markdown file
   - Report includes all LLM-powered sections

### Simple Mode (app.py):
- Single query/answer interface
- No report generation
- Good for quick questions

---

## 📊 Verified Working Features

✅ **Gemini 2.5 Flash LLM** - Connected and working
✅ **ChemicalAgent** - Answers compound and drug questions
✅ **ClinicalAgent** - Answers clinical trial and regulatory questions
✅ **LiteratureAgent** - Answers research and literature questions
✅ **GeneAgent** - Answers genetics and target biology questions
✅ **DataAgent** - Answers statistical and data analysis questions
✅ **Report Generation** - Creates comprehensive CI reports with LLM sections

---

## 🧪 Test the System

Run quick verification:
```bash
python test_quick.py
```

Expected output:
```
[1/3] Testing Gemini 2.5 Flash...           [OK]
[2/3] Testing ChemicalAgent...              [OK]
[3/3] Testing Report Generation...          [OK]

SUCCESS: All core components working!
```

---

## ⚠️ Important Notes

### Rate Limits (Free Tier)
- **20 requests per day** for Gemini 2.5 Flash free tier
- If you hit the limit, wait or upgrade to paid tier
- Error messages will show remaining wait time

### API Key
- Already configured in `config.py`
- Also available in `.env` file
- Using: `AIzaSyCR4oXUwMV8SUwh2UYC-ouh_0cN6LdRcZE`

---

## 📝 Example Queries

### Chemistry Questions
- "What is the molecular formula of ibuprofen?"
- "Explain the mechanism of action of statins"
- "What are the ADMET properties to consider for drug development?"

### Clinical Questions
- "What are the phases of clinical trials?"
- "How does FDA drug approval work?"
- "What are common adverse events for NSAIDs?"

### Genetics Questions
- "What is the function of the TP53 gene?"
- "Explain BRCA1 and breast cancer risk"
- "What are SNPs and how are they used in drug development?"

### Literature Questions
- "What is the current research on Alzheimer's disease?"
- "How do meta-analyses work?"
- "What makes a good systematic review?"

### Data Questions
- "How do you calculate statistical significance?"
- "What is the difference between correlation and causation?"
- "How do you analyze clinical trial data?"

---

## 🔧 Troubleshooting

### "LLM not ready" error
- Check that Gemini API key is set in `config.py` or `.env`
- Verify internet connection

### "Rate limit exceeded"
- You've used 20 requests today (free tier limit)
- Wait for the timer shown in error message
- Or upgrade to paid tier at https://aistudio.google.com

### Agents not responding
- Check `test_quick.py` output to diagnose
- Verify all agent files are present in `agents/` folder

---

## 📚 Additional Files

- `IMPLEMENTATION_SUMMARY.md` - Detailed technical summary
- `test_quick.py` - Quick system verification test
- `test_system.py` - Comprehensive agent testing
- `test_quick_report.md` - Sample generated report

---

## 🎯 What's Working

1. **All 5 Specialized Agents** - Real LLM-powered responses
2. **Multi-Agent Orchestration** - Synthesizes multiple agent results
3. **Report Generation** - Professional CI reports with:
   - Executive summaries
   - Key findings
   - Competitive landscape
   - Strategic recommendations
4. **Streamlit UI** - Interactive chat interface

---

## 🚀 Ready to Go!

The system is fully operational. For FULL report generation, run:

```bash
streamlit run app_v2.py
```

Then:
1. Start a session
2. Ask multiple research questions
3. Click "Generate Report"
4. Download your full CI report!

**All agents, orchestration, and LLM-powered report sections are working!**

---

*Last Updated: 2026-01-30*
*Status: ✅ FULLY OPERATIONAL*
