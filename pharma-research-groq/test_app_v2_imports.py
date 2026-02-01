"""Test all app_v2.py imports to catch missing dependencies."""
import sys
sys.path.insert(0, 'C:\\Users\\moumi\\BU-Senior-Design-EMD-Serono\\streamlit-app')

print("Testing app_v2.py imports...")
print("-" * 60)

try:
    print("[1/10] Testing streamlit...")
    import streamlit as st
    print("   OK: streamlit")
except Exception as e:
    print(f"   FAIL: {e}")
    sys.exit(1)

try:
    print("[2/10] Testing asyncio...")
    import asyncio
    print("   OK: asyncio")
except Exception as e:
    print(f"   FAIL: {e}")
    sys.exit(1)

try:
    print("[3/10] Testing config...")
    import config
    print("   OK: config")
except Exception as e:
    print(f"   FAIL: {e}")
    sys.exit(1)

try:
    print("[4/10] Testing utils.llm_factory...")
    from utils.llm_factory import get_llm, validate_llm_setup
    print("   OK: utils.llm_factory")
except Exception as e:
    print(f"   FAIL: {e}")
    sys.exit(1)

try:
    print("[5/10] Testing models...")
    from models.session import ResearchSession, QueryContext
    from models.entities import Entity, EntityType
    print("   OK: models")
except Exception as e:
    print(f"   FAIL: {e}")
    sys.exit(1)

try:
    print("[6/10] Testing context (session management)...")
    from context import PersistentSessionManager, VectorStore, MemoryRetriever
    print("   OK: context")
except Exception as e:
    print(f"   FAIL: {e}")
    sys.exit(1)

try:
    print("[7/10] Testing agents...")
    from agents.chemical_agent import ChemicalAgent
    from agents.clinical_agent import ClinicalAgent
    from agents.literature_agent import LiteratureAgent
    from agents.gene_agent import GeneAgent
    from agents.data_agent import DataAgent
    from agents.orchestrator_agent import OrchestratorAgent
    print("   OK: agents")
except Exception as e:
    print(f"   FAIL: {e}")
    sys.exit(1)

try:
    print("[8/10] Testing reporting...")
    from reporting import ReportGenerator, ReportType, ReportFormat
    print("   OK: reporting")
except Exception as e:
    print(f"   FAIL: {e}")
    sys.exit(1)

try:
    print("[9/10] Testing governance...")
    from governance import ContextForgeGateway
    print("   OK: governance")
except Exception as e:
    print(f"   FAIL: {e}")
    sys.exit(1)

print("[10/10] Testing ui...")
print("   SKIPPED: ui not used by app_v2.py")

print("-" * 60)
print("SUCCESS: All app_v2.py imports working!")
print("-" * 60)
print("\napp_v2.py is ready to run!")
print("\nRun it with:")
print("  streamlit run app_v2.py")
