"""
Configuration for the Streamlit MCP Agent application.
"""

import os
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv

    # Get the directory where config.py is located
    config_dir = Path(__file__).parent
    env_path = config_dir / '.env'

    # Load .env file with explicit path
    loaded = load_dotenv(dotenv_path=env_path, override=True)

    print(f"[DEBUG config.py] .env file path: {env_path}")
    print(f"[DEBUG config.py] .env exists: {env_path.exists()}")
    print(f"[DEBUG config.py] load_dotenv result: {loaded}")

except ImportError as e:
    # python-dotenv not installed, will only use system environment variables
    print(f"[DEBUG config.py] ImportError: {e}")
    print("[DEBUG config.py] python-dotenv not available, using system env vars only")
except Exception as e:
    print(f"[DEBUG config.py] Unexpected error loading .env: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

# === LLM Settings ===
# Using Groq API - FREE with 14,400 requests/day! (720x more than Gemini)

# Groq Settings (PRIMARY PROVIDER - FREE TIER)
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or ""
GROQ_MODEL = "llama-3.1-8b-instant"  # Fast, accurate, 14,400 requests/day FREE
GROQ_TEMPERATURE = 0.7
GROQ_MAX_TOKENS = 8192

# DEBUG: Print API key status
print(f"[DEBUG config.py] GROQ_API_KEY after load: {'SET (' + GROQ_API_KEY[:15] + '...)' if GROQ_API_KEY else 'NOT SET'}")

# Gemini Settings (BACKUP - only 20 requests/day)
# Try .env first, then fallback to hardcoded (temporary)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or "AIzaSyCR4oXUwMV8SUwh2UYC-ouh_0cN6LdRcZE"
GEMINI_MODEL = "gemini-2.5-flash"  # Free tier: Hybrid reasoning, 1M context, thinking budgets
GEMINI_TEMPERATURE = 0.7
GEMINI_MAX_OUTPUT_TOKENS = 8192

# Legacy Ollama settings (DEPRECATED - kept for reference only)
# OLLAMA_BASE_URL = "http://localhost:11434"
# OLLAMA_MODEL = "llama3.2"

# LLM Provider selection
LLM_PROVIDER = "groq"  # Options: "groq" (14,400 RPD FREE), "gemini" (20 RPD), "ollama" (deprecated)

# MCP Server configurations
MCP_SERVERS = {
    "pubchem": {
        "command": "node",
        "args": ["../servers/pubchem/index.js"],
        "description": "PubChem MCP server for chemical compound data"
    },
    "biomcp": {
        "command": "python",
        "args": ["-m", "biomcp", "run"],
        "description": "BioMCP server - Comprehensive biomedical research (PubMed, clinical trials, variants, genes)"
    },
    "literature": {
        "command": "node",
        "args": ["../servers/literature/index.js"],
        "description": "Literature MCP server for PubMed articles, abstracts, and citations"
    },
    "data_analysis": {
        "command": "node",
        "args": ["../servers/data_analysis/index.js"],
        "description": "Data Analysis MCP server for statistics, correlations, sequence analysis, and molecular descriptors"
    },
    "web_knowledge": {
        "command": "node",
        "args": ["../servers/web_knowledge/index.js"],
        "description": "Web/Knowledge MCP server for Wikipedia, clinical trials, gene info, and drug information"
    }
}

# Persistent Context Layer (Phase 1)
DATABASE_PATH = "data/sessions.db"
VECTOR_STORE_PATH = "data/chroma"

# Feature Flags - Enable/disable new features
FEATURE_FLAGS = {
    "use_persistent_context": False,     # Phase 1: SQLite + ChromaDB (disabled - download timeout issue)
    "use_specialized_agents": True,      # Phase 1: Chemical, Clinical, etc. - WORKING
    "use_governance_gateway": False,     # Phase 2: Context Forge Gateway (optional)
    "use_langgraph_orchestrator": True,  # Phase 3: Orchestrator - REQUIRED for queries
    "use_bidirectional_learning": False, # Phase 4: MCP-Agent learning (future)
    "enable_reporting": True,            # Phase 5: PDF/Markdown reports - WORKING
    "enable_ui_v2": False               # Phase 6: Enhanced UI (future)
}

# Agent settings
AGENT_MAX_ITERATIONS = 10
AGENT_VERBOSE = True

# Additional MCP Servers (from research)
EXTENDED_MCP_SERVERS = {
    "chembl": {
        "command": "node",
        "args": ["../servers/chembl/index.js"],
        "description": "ChEMBL MCP server for bioactivity and target data"
    },
    "semanticscholar": {
        "command": "node",
        "args": ["../servers/semanticscholar/index.js"],
        "description": "Semantic Scholar MCP for citations and paper recommendations"
    },
    "jupyter": {
        "command": "python",
        "args": ["-m", "jupyter_mcp"],
        "description": "Jupyter MCP for Python code execution and data analysis"
    },
    "duckdb": {
        "command": "python",
        "args": ["-m", "duckdb_mcp"],
        "description": "DuckDB MCP for SQL analytics on local files"
    },
    "brave": {
        "command": "node",
        "args": ["../servers/brave/index.js"],
        "description": "Brave Search MCP for web/news search"
    },
    "playwright": {
        "command": "node",
        "args": ["../servers/playwright/index.js"],
        "description": "Playwright MCP for web automation and dashboard access"
    }
}

# Governance settings (Phase 2)
GOVERNANCE_CONFIG = {
    "enable_audit_logging": True,
    "audit_retention_days": 90,
    "enable_compliance_checks": True,
    "enable_rate_limiting": True,
    "rate_limit_per_user": 100,  # queries per hour
    "enable_pii_detection": True
}
