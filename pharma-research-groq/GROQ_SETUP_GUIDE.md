# Groq API Setup Guide

## Why Groq?

**Problem:** Gemini free tier only offers ~20 requests per day, which is insufficient for pharmaceutical research workflows.

**Solution:** Groq API offers **14,400 FREE requests per day** - that's **720x more than Gemini!**

### Groq Advantages:
- ✅ **14,400 requests/day FREE** (vs Gemini's 20)
- ✅ **No credit card required**
- ✅ **OpenAI-compatible API**
- ✅ **Fast inference** (optimized hardware)
- ✅ **Multiple models:** Llama 3.3 70B, Llama 3.1 8B, Gemma2 9B
- ✅ **LangChain integration** via `langchain-groq`

---

## Quick Start (5 minutes)

### Step 1: Get Your FREE Groq API Key

1. Go to: **https://console.groq.com/keys**
2. Sign up (FREE, no credit card required)
3. Click "Create API Key"
4. Copy your API key

### Step 2: Add API Key to .env File

Edit `.env` in the `pharma-research-groq` directory:

```bash
# Groq API Key (PRIMARY - FREE with 14,400 requests/day!)
GROQ_API_KEY=gsk_YOUR_KEY_HERE

# Gemini API Key (BACKUP - only 20 requests/day)
GEMINI_API_KEY=AIzaSyCR4oXUwMV8SUwh2UYC-ouh_0cN6LdRcZE
```

Replace `gsk_YOUR_KEY_HERE` with your actual Groq API key.

### Step 3: Test Connection

```bash
cd pharma-research-groq
venv/Scripts/python.exe test_groq_connection.py
```

You should see:
```
✅ SUCCESS - Groq is fully operational!
🎉 You now have 14400 FREE requests per day with Groq!
```

### Step 4: Run the Application

```bash
streamlit run app_v2.py
```

---

## Configuration Details

The system is now configured to use Groq as the primary LLM provider:

**File: `config.py`**
```python
# LLM Provider selection
LLM_PROVIDER = "groq"  # Primary: Groq (14,400 RPD FREE)

# Groq Settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"  # Fast, accurate
GROQ_TEMPERATURE = 0.7
GROQ_MAX_TOKENS = 8192
```

**File: `utils/llm_factory.py`**
- Added `_get_groq_llm()` function
- Updated `get_llm()` to support "groq" provider
- Updated `validate_llm_setup()` for Groq validation

---

## Testing Checklist

### ✅ Basic Tests

1. **Test Groq Connection:**
   ```bash
   venv/Scripts/python.exe test_groq_connection.py
   ```

2. **Test Orchestrator Initialization:**
   ```bash
   venv/Scripts/python.exe test_orchestrator_init.py
   ```

3. **Test Simple Query:**
   ```bash
   venv/Scripts/python.exe test_quick.py
   ```

### ✅ Full Workflow Tests

4. **Test Multi-Agent Workflow:**
   ```bash
   venv/Scripts/python.exe test_full_workflow.py
   ```

5. **Test Streamlit Frontend:**
   ```bash
   streamlit run app_v2.py
   ```
   - Ask a research question (e.g., "What is aspirin?")
   - Verify agents execute and synthesize response
   - Check system shows "✅ LLM Ready: llama-3.1-8b-instant"

6. **Test Report Generation:**
   - In Streamlit sidebar, click "Generate Report"
   - Select "Competitive Intelligence"
   - Download and verify report content

---

## Troubleshooting

### Error: "GROQ_API_KEY environment variable not set"

**Solution:**
1. Verify `.env` file exists in `pharma-research-groq` directory
2. Check `.env` contains: `GROQ_API_KEY=gsk_...`
3. Restart the application

### Error: "langchain-groq is required"

**Solution:**
```bash
venv/Scripts/python.exe -m pip install langchain-groq
```

### Error: Rate limit exceeded

**Solution:**
- Groq free tier: 14,400 requests/day
- If exceeded, wait until next day (resets at midnight UTC)
- Or upgrade to Groq paid tier for higher limits

---

## Groq Models Available

| Model | Description | Speed | Context | Best For |
|-------|-------------|-------|---------|----------|
| `llama-3.1-8b-instant` | **DEFAULT** - Fast, accurate | ⚡⚡⚡ | 128k | General queries |
| `llama-3.3-70b-versatile` | Most capable | ⚡⚡ | 128k | Complex reasoning |
| `gemma2-9b-it` | Google's Gemma | ⚡⚡⚡ | 8k | Instruction following |
| `mixtral-8x7b-32768` | Mixture of Experts | ⚡⚡ | 32k | Specialized tasks |

To change model, edit `config.py`:
```python
GROQ_MODEL = "llama-3.3-70b-versatile"  # For complex research
```

---

## Rate Limits Comparison

| Provider | Free Tier Requests/Day | Paid Tier |
|----------|------------------------|-----------|
| **Groq** | **14,400** ✅ | $0.05-0.27 / 1M tokens |
| Gemini | 20 ❌ | $0.075-1.25 / 1M tokens |
| OpenAI GPT-4 | 0 (paid only) | $5-10 / 1M tokens |

**Winner:** Groq offers the best free tier for research workflows!

---

## Next Steps

1. ✅ Get Groq API key
2. ✅ Update `.env` file
3. ✅ Test connection: `test_groq_connection.py`
4. ✅ Run full workflow: `test_full_workflow.py`
5. ✅ Test Streamlit: `streamlit run app_v2.py`
6. ✅ Generate a report to verify end-to-end functionality
7. 🚀 Start using the system for pharmaceutical research!

---

## Support

- **Groq Documentation:** https://console.groq.com/docs
- **Groq API Status:** https://status.groq.com/
- **LangChain Groq:** https://python.langchain.com/docs/integrations/chat/groq

---

**Generated:** 2026-01-31
**Branch:** `groq-free-llm-pharma-research`
**System:** Pharmaceutical Research Intelligence with Dual Orchestration
