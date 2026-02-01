"""
Streamlit MCP Agent Application

A prototype application that uses LangChain agents with Google Gemini to query
MCP servers (like PubChem) for chemical compound information.

UPDATED: Now uses Google Gemini 2.5 Flash instead of Ollama
"""

import streamlit as st
import asyncio
from typing import Optional
from agent import MCPAgent
from mcp_tools import initialize_mcp_tools
from config import MCP_SERVERS, LLM_PROVIDER, GEMINI_MODEL
from utils.llm_factory import validate_llm_setup


# Page configuration
st.set_page_config(
    page_title="MCP Agent - Chemical Compound Query",
    page_icon="🧪",
    layout="wide"
)


@st.cache_resource
def initialize_agent():
    """Initialize the MCP agent with tools from configured servers."""
    with st.spinner("Initializing agent..."):
        try:
            # Try to initialize MCP tools asynchronously
            tools = []
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                tools = loop.run_until_complete(initialize_mcp_tools(MCP_SERVERS))
                loop.close()

                if tools:
                    st.info(f"✅ Connected to MCP servers, loaded {len(tools)} tools")
            except Exception as mcp_error:
                st.warning(f"⚠️ MCP servers not available: {str(mcp_error)}")
                st.info("💡 Running in direct LLM mode without MCP tools")

            # Create agent (works with or without tools)
            agent = MCPAgent(tools if tools else [])
            return agent

        except Exception as e:
            st.error(f"Failed to initialize agent: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            return None


def display_intermediate_steps(steps):
    """Display the agent's reasoning process."""
    if not steps:
        return

    with st.expander("🔍 View Agent Reasoning Process", expanded=False):
        for i, (action, observation) in enumerate(steps, 1):
            st.markdown(f"**Step {i}:**")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Action:**")
                st.code(f"Tool: {action.tool}\nInput: {action.tool_input}", language="text")

            with col2:
                st.markdown("**Observation:**")
                st.code(observation, language="text")

            st.divider()


def main():
    """Main Streamlit application."""

    # Header
    st.title("🧪 MCP Agent - Pharmaceutical Research Assistant")
    st.markdown(
        """
        This application uses a LangChain agent powered by **Google Gemini 2.5 Flash** for pharmaceutical
        research, chemistry, and drug development queries. Optionally connects to MCP servers for enhanced data access.
        """
    )

    # Sidebar with configuration info
    with st.sidebar:
        st.header("⚙️ Configuration")

        # LLM validation
        llm_validation = validate_llm_setup()
        if llm_validation["ready"]:
            st.success(f"✅ LLM Ready: {llm_validation.get('model', 'N/A')}")
        else:
            st.error("❌ LLM Not Ready")
            for error in llm_validation.get("errors", []):
                st.error(error)

        st.markdown(f"**Provider:** {LLM_PROVIDER}")
        st.markdown(f"**Model:** {GEMINI_MODEL}")
        st.markdown(f"**MCP Servers:**")
        for server_name, config in MCP_SERVERS.items():
            st.markdown(f"- {server_name}: {config.get('description', 'N/A')}")

        st.divider()

        st.header("📚 Example Queries")
        st.markdown(
            """
            **Chemistry:**
            - What is the molecular formula of aspirin?
            - Explain the mechanism of action of ibuprofen

            **Drug Development:**
            - What are the phases of clinical trials?
            - Explain the concept of bioavailability

            **Biology:**
            - How does CRISPR gene editing work?
            - What is the role of p53 in cancer?
            """
        )

        st.divider()

        st.header("ℹ️ About")
        st.markdown(
            """
            This is a prototype that demonstrates:
            - **LangChain agents** - Intelligent query routing
            - **Google Gemini 2.5 Flash** - Advanced LLM
            - **MCP server integration** - Optional data sources
            - **Pharmaceutical research** - Chemistry, biology, drug development

            **Current Status:**
            - ✅ Gemini LLM fully operational
            - ⚠️ MCP servers optional (enhanced features)
            """
        )

    # Initialize agent
    agent = initialize_agent()

    if agent is None:
        st.error("Failed to initialize agent. Please check your configuration.")
        st.markdown(
            """
            Make sure:
            1. GEMINI_API_KEY is set in `.env` file or config.py
            2. Required packages are installed (`pip install -r requirements.txt`)
            """
        )
        return

    # Display available tools
    with st.expander("🛠️ Available Tools", expanded=False):
        tools = agent.get_available_tools()
        if tools:
            for tool in tools:
                st.markdown(f"- `{tool}`")
        else:
            st.warning("No tools available")

    st.divider()

    # Query interface
    st.header("💬 Ask a Question")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "steps" in message and message["steps"]:
                display_intermediate_steps(message["steps"])

    # Chat input
    if prompt := st.chat_input("Ask about a chemical compound..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get agent response
        with st.chat_message("assistant"):
            with st.spinner("Thinking and querying MCP servers..."):
                result = agent.query(prompt)

                # Display response
                response = result.get("output", "No response generated")
                st.markdown(response)

                # Display intermediate steps
                steps = result.get("intermediate_steps", [])
                if steps:
                    display_intermediate_steps(steps)

                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response,
                    "steps": steps
                })

    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()


if __name__ == "__main__":
    main()
