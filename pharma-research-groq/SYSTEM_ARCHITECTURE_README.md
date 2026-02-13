# Pharmaceutical Research Intelligence System
## Architecture & Tech Stack Overview

**Version:** 1.0.0
**Last Updated:** 2026-02-06
**Status:** ✅ Production Ready

---

## 🎯 System Overview

Multi-agent pharmaceutical research intelligence platform with dual orchestration architecture. Provides competitive intelligence, drug analysis, and strategic market insights using LLM-powered specialized agents.

**Key Capabilities:**
- Multi-agent orchestration (5 specialized agents)
- Competitive intelligence report generation
- Real-time pharmaceutical research synthesis
- Session-based research workflows
- Comprehensive market analysis

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Streamlit Web UI (app_v2.py)              │
│  - Chat interface                                           │
│  - Session management                                       │
│  - Report generation UI                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              LLM Layer (utils/llm_factory.py)               │
│  Provider: Groq API                                         │
│  Model: llama-3.1-70b-versatile                            │
│  Rate: 14,400 requests/day FREE                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Orchestrator Agent (LangGraph State Machine)        │
│  - Query complexity analysis                                │
│  - Dynamic agent assignment (1-5 agents)                    │
│  - Result synthesis                                         │
└────────────┬────────────────────────────────────────────────┘
             │
             ├──────────┬──────────┬──────────┬──────────┐
             ▼          ▼          ▼          ▼          ▼
     ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
     │ Chemical │ │ Clinical │ │Literature│ │   Gene   │ │   Data   │
     │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │ │  Agent   │
     └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
          │             │             │             │             │
          └─────────────┴─────────────┴─────────────┴─────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │   Session Manager & Context  │
                    │   (In-memory storage)        │
                    └──────────────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │      Report Generator        │
                    │   (Markdown/PDF export)      │
                    └──────────────────────────────┘
```

---

## 💻 Tech Stack

### **Core Framework**
| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Frontend** | Streamlit | 1.50.0 | Web UI and chat interface |
| **Orchestration** | LangGraph | 0.2.0+ | State machine for agent coordination |
| **LLM Framework** | LangChain | 0.1.0+ | Agent framework and LLM integration |
| **LLM Provider** | Groq API | - | Free tier: 14,400 requests/day |
| **Language** | Python | 3.11.9 | Core application language |

### **LLM Configuration**
```python
Provider: Groq API
Model: llama-3.1-70b-versatile
Context: 128k tokens
Temperature: 0.7
Max Tokens: 8192
Rate Limit: 14,400 requests/day (FREE)
Token Limit: 100,000 tokens/day (FREE)
```

### **Key Libraries**
```
langchain>=0.1.0              # Agent framework
langchain-core>=0.1.0         # Core LangChain components
langchain-groq>=1.1.1         # Groq LLM integration
langgraph>=0.2.0              # State machine orchestration
streamlit>=1.32.0             # Web UI
pydantic>=2.0.0               # Data validation
python-dotenv>=1.0.0          # Environment configuration
```

### **Optional/Future**
```
mcp>=0.9.0                    # MCP server integration (planned)
biomcp-python>=0.7.0          # Biomedical MCP tools (planned)
sqlalchemy>=2.0.0             # Database ORM (planned)
chromadb>=0.4.0               # Vector storage (planned)
```

---

## 🤖 Agent System

### **5 Specialized Agents**

#### 1. **ChemicalAgent** 🧪
**Expertise:** Molecular structure, drug properties, pharmacokinetics

**Keywords:**
- compound, molecule, structure, formula, SMILES, InChI
- mechanism, pharmacology, ADMET, bioavailability
- chemical, synthesis, metabolite

**MCP Servers:**
- `pubchem` - Chemical compound database
- `chembl` - Bioactivity and SAR data (planned)

**Available Tools (12+):**
- `compound_lookup` - Retrieve compound data by name/CID
- `properties_lookup` - Get molecular properties
- `structure_search` - SMILES/InChI structure search
- `similar_compounds` - Find structurally similar compounds
- `bioactivity_data` - Get target bioactivity
- `admet_prediction` - ADMET property prediction
- `patent_search` - Patent landscape analysis
- `synthesis_routes` - Synthetic route planning

**Output:** Chemical formulas, ADMET properties, molecular analysis, SAR data

---

#### 2. **ClinicalAgent** 🏥
**Expertise:** Clinical trials, FDA approval, dosing, efficacy

**Keywords:**
- trial, clinical, phase, FDA, EMA, approval
- efficacy, safety, adverse, contraindication
- dosing, administration, indication
- randomized, placebo, double-blind

**MCP Servers:**
- `biomcp` - ClinicalTrials.gov data
- `web_knowledge` - Clinical trial registries (planned)

**Available Tools (10+):**
- `search_trials` - Search ClinicalTrials.gov
- `trial_details` - Get detailed trial information
- `drug_approval_status` - FDA/EMA approval data
- `adverse_events` - Safety profile analysis
- `dosing_guidelines` - Recommended dosing
- `indication_search` - Approved indications
- `phase_analysis` - Pipeline phase distribution
- `efficacy_metrics` - Endpoint data (response rates, survival)

**Output:** Trial results, regulatory status, clinical guidelines, safety profiles

---

#### 3. **LiteratureAgent** 📚
**Expertise:** Research papers, publications, citations

**Keywords:**
- literature, paper, study, publication, journal
- research, findings, results, conclusion
- meta-analysis, review, systematic
- PubMed, citation, impact

**MCP Servers:**
- `literature` - PubMed/scientific literature
- `biomcp` - PubMed article search
- `semanticscholar` - Citation network (planned)

**Available Tools (8+):**
- `search_pubmed` - Search PubMed articles
- `get_abstract` - Retrieve article abstracts
- `citation_analysis` - Citation network analysis
- `author_search` - Find papers by author
- `journal_lookup` - Journal impact factors
- `trending_topics` - Emerging research trends
- `meta_analysis` - Aggregate study findings
- `full_text_fetch` - Full article retrieval (if available)

**Output:** Key findings from scientific literature, trends, research summaries

---

#### 4. **GeneAgent** 🧬
**Expertise:** Genetics, biomarkers, target biology

**Keywords:**
- gene, genetic, genomic, variant, SNP
- biomarker, pharmacogenomics, target
- pathway, expression, mutation
- GWAS, allele, polymorphism

**MCP Servers:**
- `biomcp` - Gene/variant databases
- `web_knowledge` - Gene information (planned)

**Available Tools (10+):**
- `gene_lookup` - Gene information (function, location)
- `variant_search` - Find genetic variants
- `pathway_analysis` - Biological pathway mapping
- `drug_target_info` - Target-drug relationships
- `pharmacogenomics` - Drug response genetics
- `expression_data` - Gene expression patterns
- `protein_structure` - 3D protein structures
- `biomarker_discovery` - Clinical biomarker identification
- `gwas_lookup` - GWAS association data

**Output:** Genetic factors, pharmacogenomics, pathway analysis, biomarkers

---

#### 5. **DataAgent** 📊
**Expertise:** Statistical analysis, trends, data interpretation

**Keywords:**
- statistics, data, analysis, analytics
- correlation, regression, significance
- trend, pattern, distribution
- mean, median, variance, p-value
- compare, calculate, aggregate

**MCP Servers:**
- `jupyter` - Python/pandas code execution (planned)
- `duckdb` - SQL analytics on local data (planned)
- `playwright` - Dashboard data extraction (planned)

**Available Tools (12+):**
- `statistical_analysis` - Descriptive/inferential stats
- `correlation_analysis` - Find correlations
- `trend_analysis` - Time-series trends
- `comparative_stats` - Compare groups/treatments
- `distribution_analysis` - Data distributions
- `regression_analysis` - Linear/logistic regression
- `hypothesis_testing` - T-tests, ANOVA, chi-square
- `visualization` - Plot generation (planned)
- `sql_query` - SQL-based data queries
- `pandas_operations` - DataFrame manipulation

**Output:** Statistical insights, market trends, comparative analysis, visualizations

### **Agent Selection Logic**

```python
Query Complexity → Agent Count
- Simple: 1 agent
- Moderate: 3 agents
- Complex: 5 agents (all)

Score Threshold: >= 0.3
Selection: Top N agents by score
```

---

## 🔌 MCP (Model Context Protocol) Architecture

### **MCP Server Ecosystem**

MCP servers provide specialized data access and tools to agents. Currently using **LLM-based simulation** (agents use their LLM expertise); **real MCP servers planned** for Phase 2.

#### **Configured MCP Servers (config.py)**

```python
MCP_SERVERS = {
    "pubchem": {
        "command": "node",
        "args": ["../servers/pubchem/index.js"],
        "description": "Chemical compound data (PubChem database)"
    },
    "biomcp": {
        "command": "python",
        "args": ["-m", "biomcp", "run"],
        "description": "Biomedical research (PubMed, trials, genes, variants)"
    },
    "literature": {
        "command": "node",
        "args": ["../servers/literature/index.js"],
        "description": "PubMed articles, abstracts, citations"
    },
    "data_analysis": {
        "command": "node",
        "args": ["../servers/data_analysis/index.js"],
        "description": "Statistics, correlations, molecular descriptors"
    },
    "web_knowledge": {
        "command": "node",
        "args": ["../servers/web_knowledge/index.js"],
        "description": "Wikipedia, clinical trials, gene info, drug databases"
    }
}
```

#### **Extended MCP Servers (Planned)**

```python
EXTENDED_MCP_SERVERS = {
    "chembl": {
        "description": "Bioactivity and target data from ChEMBL"
    },
    "semanticscholar": {
        "description": "Citation network and paper recommendations"
    },
    "jupyter": {
        "description": "Python code execution for data analysis"
    },
    "duckdb": {
        "description": "SQL analytics on local CSV/Parquet files"
    },
    "brave": {
        "description": "Web/news search for market intelligence"
    },
    "playwright": {
        "description": "Web automation and dashboard data extraction"
    }
}
```

### **MCP Integration Status**

| MCP Server | Status | Agent(s) | Tools Available |
|------------|--------|----------|-----------------|
| **pubchem** | 🟡 Configured | ChemicalAgent | 12+ compound tools |
| **biomcp** | 🟡 Configured | Clinical, Gene, Literature | 25+ biomedical tools |
| **literature** | 🟡 Configured | LiteratureAgent | 8+ PubMed tools |
| **data_analysis** | 🟡 Configured | DataAgent | 12+ analytics tools |
| **web_knowledge** | 🟡 Configured | Clinical, Gene | 10+ knowledge tools |
| **chembl** | ⚪ Planned | ChemicalAgent | Bioactivity data |
| **jupyter** | ⚪ Planned | DataAgent | Python execution |
| **duckdb** | ⚪ Planned | DataAgent | SQL analytics |

**Legend:**
- 🟢 Active (connected and tested)
- 🟡 Configured (server defined, using LLM simulation)
- ⚪ Planned (not yet implemented)

### **Current Implementation**

**Phase 1 (Current):** Agents use **LLM-based expertise** to simulate tool outputs
- ✅ Fast prototyping and testing
- ✅ No external dependencies
- ✅ Works with any Groq model
- ⚠️ Synthesized data (not real-time)

**Phase 2 (Planned):** Real MCP server connections
- 🔄 Live data from PubChem, ClinicalTrials.gov, PubMed
- 🔄 Real-time compound lookups
- 🔄 Actual clinical trial data
- 🔄 Direct database queries

### **Tool Invocation Flow**

```python
# Current (LLM-based simulation)
User Query
    ↓
Agent receives task
    ↓
Agent builds specialized prompt with domain expertise
    ↓
LLM generates expert response
    ↓
Result returned to orchestrator

# Future (Real MCP servers)
User Query
    ↓
Agent receives task
    ↓
Agent selects appropriate MCP tool
    ↓
MCP server executes tool (e.g., PubChem lookup)
    ↓
Real data returned
    ↓
Agent synthesizes with LLM
    ↓
Result returned to orchestrator
```

---

## 📁 Project Structure

```
pharma-research-groq/
├── agents/                          # Specialized agent implementations
│   ├── base_agent.py               # Abstract base class
│   ├── orchestrator_agent.py       # LangGraph orchestrator (MAIN)
│   ├── chemical_agent.py           # Chemical compound analysis
│   ├── clinical_agent.py           # Clinical trial analysis
│   ├── literature_agent.py         # Literature search
│   ├── gene_agent.py               # Genetic analysis
│   └── data_agent.py               # Statistical analysis
├── reporting/                       # Report generation
│   ├── report_generator.py         # Main report engine
│   └── exporters/                  # Format exporters
│       ├── markdown_exporter.py
│       └── pdf_exporter.py
├── orchestration/                   # Orchestration utilities
│   ├── session_manager.py          # Session state management
│   └── performance_kb.py           # Performance tracking
├── utils/                          # Utilities
│   ├── llm_factory.py              # LLM initialization (CRITICAL)
│   └── cache.py                    # Caching utilities
├── governance/                     # Governance layer (optional)
│   ├── gateway.py                  # Context forge gateway
│   ├── audit_logger.py             # Audit logging
│   └── compliance_engine.py        # Compliance checks
├── context/                        # Context management (planned)
│   ├── session_db.py               # SQLite storage
│   └── vector_store.py             # ChromaDB integration
├── models/                         # Data models
│   └── entities.py                 # Entity definitions
├── venv/                           # Virtual environment
├── config.py                       # Configuration (CRITICAL)
├── app_v2.py                       # Main Streamlit app (ENTRY POINT)
├── .env                            # API keys (NOT in git)
├── requirements.txt                # Python dependencies
└── run.bat                         # Windows startup script
```

---

## ⚙️ Configuration

### **Environment Variables (.env)**
```bash
# Groq API (Primary)
GROQ_API_KEY=gsk_your_key_here

# Gemini API (Backup - optional)
GEMINI_API_KEY=your_key_here
```

### **Feature Flags (config.py)**
```python
FEATURE_FLAGS = {
    "use_persistent_context": False,      # SQLite + ChromaDB (planned)
    "use_specialized_agents": True,       # ✅ ENABLED - All 5 agents
    "use_governance_gateway": False,      # Compliance checks (optional)
    "use_langgraph_orchestrator": True,   # ✅ ENABLED - Required
    "use_bidirectional_learning": False,  # Learning feedback (planned)
    "enable_reporting": True,             # ✅ ENABLED - Report generation
    "enable_ui_v2": False                 # Enhanced UI (planned)
}
```

---

## 🚀 How to Run

### **Prerequisites**
- Python 3.11.9
- Virtual environment activated
- Groq API key (free at https://console.groq.com/keys)

### **Quick Start**
```powershell
# Navigate to project
cd C:\Users\moumi\Agentic-Comodotity-Trading-System\pharma-research-groq

# Activate virtual environment
venv\Scripts\Activate.ps1

# Run Streamlit app
streamlit run app_v2.py
```

### **Or use the batch file:**
```powershell
.\run.bat
```

**Access at:** http://localhost:8502

---

## 📊 Performance Characteristics

### **Query Processing Times**

| Complexity | Agents Used | Time (70b model) | Time (8b model) |
|------------|-------------|------------------|-----------------|
| Simple | 1 agent | 15-20s | 3-5s |
| Moderate | 3 agents | 30-45s | 10-15s |
| Complex | 5 agents | 60-90s | 20-30s |

### **Token Usage (Free Tier Limits)**

| Model | Tokens/Query | Queries/Day | Best For |
|-------|--------------|-------------|----------|
| llama-3.1-8b-instant | ~500-1000 | 100+ | Quick lookups |
| llama-3.1-70b-versatile | ~2000-4000 | 25-30 | ✅ **Recommended** |
| llama-3.3-70b-versatile | ~5000-10000 | 10-15 | Maximum quality |

### **Rate Limits**
- **Requests:** 14,400/day (6,000/hour)
- **Tokens:** 100,000/day
- **Resets:** Midnight UTC

---

## 📋 Workflow Example

### **1. Start System**
```powershell
streamlit run app_v2.py
```

### **2. Create Session**
- Sidebar → "Create New Session"
- Enter research goal: "Competitive Intelligence: GLP-1 Agonists"

### **3. Submit Query**
```
Analyze GLP-1 receptor agonists for type 2 diabetes treatment.
Include market landscape, clinical efficacy, molecular mechanisms,
and strategic recommendations.
```

### **4. System Processing**
- Query analyzed → Complexity: complex
- Agents assigned: 5/5 (all agents)
- Execution time: ~60s
- Synthesis: Comprehensive report

### **5. Generate Report**
- Sidebar → Report Type: "Competitive Intelligence"
- Click "Generate Report"
- Download: `report_[session_id].md`

### **6. Report Contents**
- Executive Summary
- Key Findings (6-8 insights)
- Competitive Landscape
- Strategic Recommendations (with impact estimates)
- Methodology

---

## 🔒 Security & Best Practices

### **API Key Management**
- ✅ Keys stored in `.env` (gitignored)
- ✅ Never commit `.env` to repository
- ✅ Use environment variables in production

### **Rate Limiting**
- ✅ Automatic retry with exponential backoff (LangChain)
- ✅ Token usage monitoring via Groq console
- ⚠️ Watch for 429 errors (rate limit exceeded)

### **Data Privacy**
- ✅ In-memory session storage (no persistence)
- ✅ No external data transmission (except to Groq API)
- ⚠️ Don't input sensitive/proprietary data

---

## 🐛 Known Issues & Limitations

### **Current Limitations**
1. **Token Limits:** 100k tokens/day on free tier (upgrade for more)
2. **No Persistence:** Sessions lost on restart (planned feature)
3. **No MCP Servers:** Real data sources not connected yet (planned)
4. **Report Format:** Markdown only (PDF planned)

### **Common Issues**

**Issue:** "Rate limit exceeded (429)"
**Solution:** Wait or switch to faster model

**Issue:** "Report button does nothing"
**Solution:** Ask a query first, then generate report

**Issue:** "Orchestrator not initialized"
**Solution:** Click "Clear Cache & Restart" in sidebar

---

## 🔄 Recent Updates

### **2026-02-06 - Production Release**
- ✅ Fixed orchestrator to use all 5 agents for complex queries
- ✅ Fixed agent selection threshold (>= 0.3 instead of > 0.3)
- ✅ Configured llama-3.1-70b-versatile as default (balanced)
- ✅ Added comprehensive error handling for reports
- ✅ Verified full workflow with competitive intelligence reports
- ✅ Documented complete system architecture

### **Key Fixes**
```python
# agents/orchestrator_agent.py
- Dynamic agent limits: 1/3/5 based on complexity
- Inclusive threshold: score >= 0.3 (was > 0.3)

# config.py
- Default model: llama-3.1-70b-versatile
- Timeout increased: 90s for complex queries
```

---

## 📚 Documentation

- **Testing Summary:** `TESTING_COMPLETE_GROQ_70B.md`
- **Model Comparison:** `TEST_MODELS.md`
- **Setup Guide:** `GROQ_SETUP_GUIDE.md`
- **Integration Details:** `GROQ_INTEGRATION_COMPLETE.md`
- **This File:** `SYSTEM_ARCHITECTURE_README.md`

---

## 🔮 Roadmap

### **Phase 1: Current (Complete)**
- ✅ Multi-agent orchestration
- ✅ LLM integration (Groq)
- ✅ Report generation
- ✅ Session management

### **Phase 2: Data Integration (Planned)**
- [ ] MCP server connections (PubChem, BioMCP)
- [ ] Real-time data fetching
- [ ] Enhanced data agent with actual data sources

### **Phase 3: Persistence (Planned)**
- [ ] SQLite session storage
- [ ] ChromaDB vector store
- [ ] Query history and caching

### **Phase 4: Advanced Features (Future)**
- [ ] PDF report export
- [ ] Multi-user support
- [ ] Advanced visualizations
- [ ] API endpoint exposure

---

## 🤝 Contributing

This is a pharmaceutical research intelligence platform. Key areas for contribution:
1. Additional specialized agents
2. Enhanced report templates
3. MCP server integrations
4. Performance optimizations
5. UI/UX improvements

---

## 📞 Support

**For Groq API Issues:**
- Console: https://console.groq.com/
- Docs: https://console.groq.com/docs
- Status: https://status.groq.com/

**For LangChain Issues:**
- Docs: https://python.langchain.com/docs

---

## 📄 License

Proprietary - Pharmaceutical Research Intelligence System

---

**System Status:** ✅ Production Ready
**Last Verified:** 2026-02-06
**Maintained By:** Development Team
**Model:** llama-3.1-70b-versatile (Groq)

---

## 🎴 Quick Reference Card

### **System Essentials**
```
Entry Point:    app_v2.py
Configuration:  config.py + .env
Port:           http://localhost:8502
Python:         3.11.9
Framework:      Streamlit + LangChain + LangGraph
```

### **Agent Summary**
```
ChemicalAgent  🧪  → PubChem, ChEMBL         → 12+ tools
ClinicalAgent  🏥  → BioMCP, Trials.gov      → 10+ tools
LiteratureAgent 📚 → PubMed, Literature      → 8+ tools
GeneAgent      🧬  → BioMCP, Gene DBs        → 10+ tools
DataAgent      📊  → Jupyter, DuckDB         → 12+ tools
```

### **LLM Configuration**
```
Provider:  Groq API (FREE)
Model:     llama-3.1-70b-versatile
Requests:  14,400/day
Tokens:    100,000/day
Context:   128k tokens
```

### **Key Commands**
```powershell
# Start system
streamlit run app_v2.py

# Activate venv
venv\Scripts\Activate.ps1

# Switch model (edit config.py)
GROQ_MODEL = "llama-3.1-70b-versatile"

# Test multi-agent
python test_multi_agent_comprehensive.py

# Test reports
python test_report_generation_comprehensive.py
```

### **Troubleshooting**
```
Rate limit error → Wait or switch to faster model
Report fails    → Ask query first, then generate
Token limit     → Wait 19min or upgrade tier
Orchestrator    → Click "Clear Cache & Restart"
```

### **File Locations**
```
Critical Files:
- config.py                        → LLM & feature config
- agents/orchestrator_agent.py     → Multi-agent logic
- utils/llm_factory.py             → LLM initialization
- app_v2.py                        → Web UI entry point
- .env                             → API keys (SECRET)

Test Files:
- test_multi_agent_comprehensive.py     → Agent tests
- test_report_generation_comprehensive.py → Report tests
- TESTING_COMPLETE_GROQ_70B.md          → Test results

Documentation:
- SYSTEM_ARCHITECTURE_README.md (this file)
- GROQ_SETUP_GUIDE.md
- TEST_MODELS.md
```

### **Agent Capabilities Matrix**

| Capability | Chemical | Clinical | Literature | Gene | Data |
|------------|----------|----------|------------|------|------|
| Compound lookup | ✅✅✅ | ➖ | ➖ | ➖ | ➖ |
| Clinical trials | ➖ | ✅✅✅ | ✅ | ➖ | ✅ |
| Literature search | ✅ | ✅ | ✅✅✅ | ✅ | ➖ |
| Genetic analysis | ➖ | ➖ | ➖ | ✅✅✅ | ➖ |
| Statistical analysis | ➖ | ✅ | ➖ | ➖ | ✅✅✅ |
| Market intelligence | ➖ | ✅ | ✅ | ➖ | ✅✅ |
| Regulatory data | ➖ | ✅✅✅ | ➖ | ➖ | ➖ |

**Legend:** ✅✅✅ Primary | ✅✅ Strong | ✅ Capable | ➖ Not applicable

---

**END OF SYSTEM ARCHITECTURE README**
