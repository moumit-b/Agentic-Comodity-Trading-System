"""
app_v2.py - Enhanced Application with Dual Orchestration Architecture

Production-ready Streamlit app with:
- Persistent context (SQLite + ChromaDB)
- Specialized agents (Chemical, Clinical, Literature, Gene, Data)
- Governance gateway (Context Forge pattern)
- LangGraph orchestration
- Bidirectional learning
- Professional reporting
"""

import streamlit as st
import asyncio
from datetime import datetime

# Import configuration
import config

# Import LLM utilities
from utils.llm_factory import get_llm, validate_llm_setup

# Phase 1: Agents (always needed)
from agents import ChemicalAgent, ClinicalAgent, LiteratureAgent, GeneAgent, DataAgent
from agents.orchestrator_agent import OrchestratorAgent

# Phase 1: Context (conditionally imported below)
# from context import PersistentSessionManager, VectorStore, MemoryRetriever

# Phase 2: Governance (conditionally imported below)
# from governance import ContextForgeGateway

# Phase 4: MCP Orchestration (placeholder for now)
# from orchestration import MCPOrchestrator

# Phase 5: Reporting
from reporting import ReportGenerator, ReportType, ReportFormat


# Page configuration
st.set_page_config(
    page_title="Context-Aware Research Intelligence System",
    page_icon="🔬",
    layout="wide"
)

# Initialize session state
if "session_id" not in st.session_state:
    # Auto-create a default session for convenience
    from datetime import datetime
    st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "initialized" not in st.session_state:
    st.session_state.initialized = False


@st.cache_resource`r`ndef initialize_system(model_name=None):
    """Initialize all system components (cached)."""
    # Check feature flags
    use_persistent = config.FEATURE_FLAGS.get("use_persistent_context", False)
    use_governance = config.FEATURE_FLAGS.get("use_governance_gateway", False)
    use_orchestrator = config.FEATURE_FLAGS.get("use_langgraph_orchestrator", False)

    # Initialize persistent context (conditionally import to avoid dependencies)
    session_manager = None
    if use_persistent:
        from context import PersistentSessionManager
        session_manager = PersistentSessionManager()

    # Initialize governance gateway (conditionally import to avoid dependencies)
    gateway = None
    if use_governance:
        from governance import ContextForgeGateway
        gateway = ContextForgeGateway()

    # Initialize orchestrator with Gemini LLM (ALWAYS ENABLED - core functionality)
    orchestrator = None
    try:
        # Initialize LLM using factory
        llm = get_llm(model=model_name)

        # For now, MCP orchestrator is a placeholder
        # TODO: Initialize real MCP orchestrator when MCP servers are connected
        mcp_orchestrator = None

        # Create orchestrator agent (required for query processing)
        orchestrator = OrchestratorAgent(
            mcp_orchestrator=mcp_orchestrator,
            governance_gateway=gateway,
            llm=llm
        )
    except Exception as e:
        st.error(f"Failed to initialize orchestrator: {e}")
        import traceback
        st.error(traceback.format_exc())
        orchestrator = None

    return {
        "session_manager": session_manager,
        "gateway": gateway,
        "orchestrator": orchestrator,
        "llm_validation": validate_llm_setup()
    }


def main():
    """Main application entry point."""

    # Title
    st.title("🔬 Context-Aware Research Intelligence System")
    st.caption("Dual Orchestration Architecture for Pharmaceutical Competitive Intelligence")

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Cache clear button
        if st.button("🔄 Clear Cache & Restart"):
            st.cache_resource.clear()
            st.rerun()

        # Model Selection`r`n        if config.LLM_PROVIDER == \"groq\":`r`n            available_models = [\"mixtral-8x7b-32768\", \"llama-3.3-70b-versatile\", \"llama-3.1-8b-instant\"]`r`n        else:`r`n            available_models = [\"gemini-2.5-flash\"]`r`n`r`n        selected_model = st.selectbox(\"Choose Model\", available_models)`r`n        system = initialize_system(model_name=selected_model)

        # LLM validation status
        llm_validation = system["llm_validation"]
        if llm_validation["ready"]:
            st.success(f"✅ LLM Ready: {llm_validation.get('model', 'N/A')}")
        else:
            st.error("❌ LLM Not Ready")
            for error in llm_validation.get("errors", []):
                st.error(error)
            st.info("💡 Set GEMINI_API_KEY environment variable to enable LLM")

        st.markdown(f"**Provider:** {config.LLM_PROVIDER}")
        st.markdown(f"**Model:** {config.GEMINI_MODEL}")

        # Orchestrator status
        if system["orchestrator"]:
            st.success("✅ Orchestrator: Ready")
        else:
            st.error("❌ Orchestrator: Not initialized")
            st.warning("⚠️ Queries will not work without orchestrator")

        st.divider()

        st.header("Session Management")

        if st.button("New Research Session"):
            if system["session_manager"]:
                session = system["session_manager"].create_session(
                    user_id="demo_user",
                    research_goal=st.text_input("Research Goal", "Drug development competitive intelligence")
                )
                st.session_state.session_id = session.session_id
                st.success(f"Session created: {session.session_id[:8]}...")

        if st.session_state.session_id:
            st.info(f"Active Session: {st.session_state.session_id[:8]}...")

            # Report generation
            st.header("Generate Report")
            report_type = st.selectbox(
                "Report Type",
                ["Competitive Intelligence", "Target CV", "Clinical Summary"]
            )

            if st.button("Generate Report"):
                if system["session_manager"]:
                    try:
                        with st.spinner("Generating report..."):
                            generator = ReportGenerator(system["session_manager"], system["llm"])
                            report = generator.generate_report(
                                st.session_state.session_id,
                                report_type=ReportType.COMPETITIVE_INTELLIGENCE,
                                format=ReportFormat.MARKDOWN
                            )
                            st.success(f"Report generated! ({len(report)} characters)")
                            st.download_button(
                                "Download Report",
                                report,
                                file_name=f"report_{st.session_state.session_id[:8]}.md",
                                mime="text/markdown"
                            )
                    except ValueError as e:
                        st.error(f"Session error: {e}")
                        st.info("Try asking a research query first, then generate the report.")
                    except Exception as e:
                        st.error(f"Error generating report: {e}")
                        import traceback
                        st.code(traceback.format_exc())

        # Feature flags display
        st.header("System Status")
        for feature, enabled in config.FEATURE_FLAGS.items():
            icon = "✅" if enabled else "❌"
            st.text(f"{icon} {feature}")

    # Main chat interface
    st.header("Research Assistant")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask a research question..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Processing query through orchestration system..."):
                # Check if orchestrator is available
                if system["orchestrator"] and st.session_state.session_id:
                    try:
                        # Use async orchestrator
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(
                            system["orchestrator"].process_query(
                                query=prompt,
                                session_id=st.session_state.session_id,
                                user_id="demo_user"
                            )
                        )
                        loop.close()

                        # Display results
                        response = result.get("final_answer", "No response generated")

                        # Show agent details in expander
                        with st.expander("🤖 Agent Execution Details"):
                            st.markdown(f"**Query Complexity:** {result.get('query_complexity', 'N/A')}")
                            st.markdown(f"**Agents Used:** {', '.join(result.get('assigned_agents', []))}")
                            st.markdown(f"**Execution Time:** {result.get('execution_time', 0):.2f}s")

                            if result.get("agent_results"):
                                for agent_result in result["agent_results"]:
                                    st.markdown(f"**{agent_result.agent_name}:**")
                                    st.json(agent_result.result_data)

                    except Exception as e:
                        response = f"Error processing query: {str(e)}\n\nPlease check LLM configuration and MCP server connections."
                        st.error(response)

                else:
                    # Fallback response when orchestrator not available
                    response = f"Query received: {prompt}\n\n"
                    response += "⚠️ **Orchestrator not enabled**\n\n"
                    response += "System is configured with:\n"
                    response += f"- LLM Ready: {system['llm_validation']['ready']}\n"
                    response += f"- Persistent Context: {config.FEATURE_FLAGS['use_persistent_context']}\n"
                    response += f"- Specialized Agents: {config.FEATURE_FLAGS['use_specialized_agents']}\n"
                    response += f"- Governance Gateway: {config.FEATURE_FLAGS['use_governance_gateway']}\n"
                    response += f"- LangGraph Orchestrator: {config.FEATURE_FLAGS['use_langgraph_orchestrator']}\n"
                    response += "\n💡 Enable feature flags in config.py to activate full orchestration."

                st.write(response)
                st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
