"""
Simple Streamlit App - Test Gemini LLM Integration

This is a minimal version to verify Gemini is working without requiring MCP servers.
"""

import streamlit as st
from config import LLM_PROVIDER, GEMINI_MODEL
from utils.llm_factory import get_llm, validate_llm_setup

# Page configuration
st.set_page_config(
    page_title="Gemini LLM Test",
    page_icon="🔬",
    layout="wide"
)

def main():
    """Main application entry point."""

    # Title
    st.title("🔬 Gemini LLM Integration Test")
    st.markdown("Testing Google Gemini 2.5 Flash integration without MCP servers")

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
            st.info("💡 Set GEMINI_API_KEY environment variable to enable LLM")

        st.markdown(f"**Provider:** {LLM_PROVIDER}")
        st.markdown(f"**Model:** {GEMINI_MODEL}")

        st.divider()

        st.header("📝 Setup Instructions")
        st.markdown("""
        1. Get API key from [Google AI Studio](https://aistudio.google.com/)
        2. Set environment variable:
           ```
           setx GEMINI_API_KEY "your_key"
           ```
        3. Restart terminal
        4. Run this app
        """)

    # Main content
    st.header("💬 Test the LLM")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask a question to test Gemini..."):
        # Check if LLM is ready
        llm_validation = validate_llm_setup()
        if not llm_validation["ready"]:
            st.error("⚠️ LLM not configured. Please set GEMINI_API_KEY environment variable.")
            st.stop()

        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get LLM response
        with st.chat_message("assistant"):
            with st.spinner("Generating response with Gemini..."):
                try:
                    # Initialize LLM
                    llm = get_llm()

                    # Generate response
                    response = llm.invoke(prompt)

                    # Extract content based on response type
                    if hasattr(response, 'content'):
                        response_text = response.content
                    else:
                        response_text = str(response)

                    st.markdown(response_text)

                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text
                    })

                except Exception as e:
                    error_msg = f"Error generating response: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })

    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()


if __name__ == "__main__":
    main()
