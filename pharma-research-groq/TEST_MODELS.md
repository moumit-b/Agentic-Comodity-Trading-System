# Groq Model Comparison for Pharmaceutical Research

## Models to Test (Ranked by Reasoning Quality)

### 1. llama-3.3-70b-versatile (RECOMMENDED for Rich Reasoning)
**Best for:** Complex analysis, deep reasoning, comprehensive synthesis
**Speed:** Slower (~10-15s per query)
**Context:** 128k tokens
**Use case:** Production pharmaceutical research

**To activate:**
Edit `config.py` line 38:
```python
GROQ_MODEL = "llama-3.3-70b-versatile"
```

---

### 2. llama-3.1-70b-versatile
**Best for:** Strong reasoning, balanced performance
**Speed:** Moderate (~8-12s per query)
**Context:** 128k tokens
**Use case:** Complex queries needing detailed analysis

**To activate:**
Edit `config.py` line 38:
```python
GROQ_MODEL = "llama-3.1-70b-versatile"
```

---

### 3. mixtral-8x7b-32768
**Best for:** Specialized reasoning (Mixture of Experts architecture)
**Speed:** Fast (~4-6s per query)
**Context:** 32k tokens
**Use case:** Multi-domain pharmaceutical analysis

**To activate:**
Edit `config.py` line 38:
```python
GROQ_MODEL = "mixtral-8x7b-32768"
```

---

### 4. llama-3.1-8b-instant (CURRENT DEFAULT)
**Best for:** Fast responses, simple queries
**Speed:** Fastest (~3-5s per query)
**Context:** 128k tokens
**Use case:** Quick lookups, simple analysis

**Already active** - no changes needed

---

## Testing Procedure

### Test Prompt (Copy & Paste)
```
Analyze aspirin as a potential treatment for rheumatoid arthritis. Provide:
1. Chemical properties and mechanism of action
2. Clinical trial data and FDA approval status
3. Comparison with other NSAIDs for RA treatment
4. Gene interactions (COX-1, COX-2 pathways)
5. Safety profile and contraindications
6. Recommendations for clinical use in RA patients
```

### For Each Model:

1. **Edit config.py** (change GROQ_MODEL)
2. **Restart Streamlit**: `venv\Scripts\streamlit.exe run app_v2.py`
3. **Click "🔄 Clear Cache & Restart"** in sidebar
4. **Paste test prompt** in chat
5. **Record observations**:
   - Response time
   - Depth of analysis
   - Accuracy
   - Agent coordination
   - Synthesis quality
6. **Generate report** (sidebar)
7. **Save output** for comparison

---

## Evaluation Criteria

| Criterion | Weight | What to Look For |
|-----------|--------|------------------|
| **Depth of Analysis** | 30% | Detailed mechanisms, comprehensive coverage |
| **Accuracy** | 25% | Correct chemical formulas, accurate clinical data |
| **Synthesis Quality** | 20% | Coherent integration of multi-agent findings |
| **Clinical Relevance** | 15% | Practical recommendations, real-world applicability |
| **Agent Coordination** | 10% | Effective use of ChemicalAgent, ClinicalAgent, GeneAgent |

---

## Expected Results

### llama-3.3-70b-versatile (Best for Rich Reasoning)
- ✅ Most comprehensive analysis
- ✅ Deep mechanistic insights
- ✅ Strong clinical recommendations
- ✅ Best synthesis across agents
- ⚠️ Slower (~10-15s)

### llama-3.1-70b-versatile
- ✅ Strong analytical depth
- ✅ Good clinical insights
- ✅ Solid synthesis
- ⚠️ Moderate speed (~8-12s)

### mixtral-8x7b-32768
- ✅ Fast with good quality
- ✅ Strong multi-domain reasoning
- ⚠️ Shorter context window (32k vs 128k)
- ⚠️ May be less comprehensive than 70B models

### llama-3.1-8b-instant (Current)
- ✅ Fastest (~3-5s)
- ⚠️ Less depth in analysis
- ⚠️ Simpler synthesis
- ⚠️ May miss nuanced connections

---

## Recommendation

**For pharmaceutical research requiring rich reasoning:**

1. **Start with:** `llama-3.3-70b-versatile`
2. **Fallback:** `llama-3.1-70b-versatile`
3. **Fast alternative:** `mixtral-8x7b-32768`

**For production:**
- Use `llama-3.3-70b-versatile` as default
- Keep `llama-3.1-8b-instant` for simple lookups
- Switch via config based on query complexity

---

## Rate Limits (All Models)

All Groq models share the **14,400 requests/day FREE** limit.

Monitor usage at: https://console.groq.com/

---

**Next:** Run the test workflow and record which model produces the richest, most accurate pharmaceutical analysis!
