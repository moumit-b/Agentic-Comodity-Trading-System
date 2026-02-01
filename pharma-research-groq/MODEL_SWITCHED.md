# Model Switched - Fresh Quota Available

## Changes Made

### 1. Switched to Gemini 2.0 Flash
**Previous:** `gemini-2.5-flash-lite` (quota exhausted)
**New:** `gemini-2.0-flash` (fresh quota, separate limit)

**Why gemini-2.0-flash?**
From the pricing doc:
> "Our most balanced multimodal model with great performance across all tasks, with a 1 million token context window, and built for the era of Agents."

- ✅ Free tier available
- ✅ Built for agent-based applications
- ✅ 1M context window
- ✅ Fresh quota (separate from flash-lite)
- ✅ More balanced performance

### 2. Added Cache Clear Button
Added "🔄 Clear Cache & Restart" button in sidebar to force re-initialization when needed.

### 3. Added Orchestrator Status Display
The sidebar now shows:
- ✅ Orchestrator: Ready (if working)
- ❌ Orchestrator: Not initialized (if failed)

---

## How to Use

### Step 1: Restart the Streamlit App
```bash
# Kill current app
taskkill /F /FI "IMAGENAME eq python.exe" /FI "MEMUSAGE gt 30000" 2>nul

# Start fresh
cd streamlit-app
streamlit run app_v2.py
```

### Step 2: Clear Cache (if needed)
If you see "Orchestrator not enabled":
1. Click "🔄 Clear Cache & Restart" button in sidebar
2. App will restart with fresh initialization

### Step 3: Verify System Status
Check the sidebar:
- ✅ LLM Ready: gemini-2.0-flash
- ✅ Orchestrator: Ready
- ✅ use_langgraph_orchestrator (System Status section)

### Step 4: Try a Query
Ask: **"What is aspirin?"**

You should now get a detailed multi-agent response!

---

## About Free Tier Quotas

### How Model Quotas Work
Each Gemini model has a **separate** request quota:
- `gemini-2.5-flash-lite`: ~20 requests/day (exhausted from testing)
- `gemini-2.0-flash`: ~20 requests/day (FRESH, just switched)
- `gemini-2.5-flash`: ~20 requests/day (fresh)
- `gemini-2.5-pro`: ~20 requests/day (fresh)

### Available Free Models
From the pricing doc, these models are all "Free of charge":
1. **gemini-2.0-flash** ← We're using this now
2. gemini-2.5-flash
3. gemini-2.5-pro
4. gemini-3-flash-preview
5. gemma-3 (open model)

### Strategy for More Requests
To maximize free tier usage across models:
1. Use gemini-2.0-flash for ~20 requests
2. When quota hits, switch to gemini-2.5-flash
3. Then switch to gemini-2.5-pro
4. Then switch to gemini-3-flash-preview
5. Next day, all quotas reset

**To switch models:**
Edit `streamlit-app/config.py` line 38:
```python
GEMINI_MODEL = "gemini-2.5-flash"  # or any other free model
```

Then click "🔄 Clear Cache & Restart" in the app.

---

## Testing the New Model

Run this to verify:
```bash
cd streamlit-app
venv/Scripts/python.exe test_orchestrator_init.py
```

Expected output:
```
SUCCESS: Orchestrator initialized correctly!
```

---

## If You Still See "Orchestrator Not Enabled"

### Option 1: Clear Cache
1. Click "🔄 Clear Cache & Restart" button in sidebar
2. Wait for app to reload

### Option 2: Full Restart
```bash
# Kill all Python processes
taskkill /F /IM python.exe

# Restart app
cd streamlit-app
streamlit run app_v2.py
```

### Option 3: Check Logs
Look for error messages in terminal where you ran `streamlit run app_v2.py`

The orchestrator initialization errors will now be displayed with full traceback.

---

## Summary

✅ **Switched to gemini-2.0-flash (fresh quota)**
✅ **Added cache clear button**
✅ **Added orchestrator status display**
✅ **Orchestrator initialization tested successfully**

**Next:** Restart the app and try your query!

---

*Date: 2026-01-30*
*Model: gemini-2.0-flash*
