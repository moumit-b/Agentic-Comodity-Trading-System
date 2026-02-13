"""
LLM Factory

Centralized LLM initialization supporting multiple providers.
Primary provider: Google Gemini 2.5 Flash
"""

import config
from typing import Optional


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
):
    """
    Get LLM instance based on configuration.

    Args:
        provider: LLM provider ("groq", "gemini", "ollama"). If None, uses config.LLM_PROVIDER
        model: Override default model name
        temperature: Override default temperature
        max_tokens: Override default max tokens

    Returns:
        LLM instance (ChatGroq, ChatGoogleGenerativeAI, or ChatOllama)

    Raises:
        ValueError: If API key is not set
        ImportError: If required packages are not installed
    """
    provider = provider or config.LLM_PROVIDER

    if provider == "groq":
        return _get_groq_llm(model, temperature, max_tokens)
    elif provider == "gemini":
        return _get_gemini_llm(model, temperature, max_tokens)
    elif provider == "ollama":
        return _get_ollama_llm(model, temperature, max_tokens)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _get_groq_llm(model=None, temperature=None, max_tokens=None):
    """Initialize Groq LLM (PRIMARY - FREE with 14,400 requests/day)."""
    import os
    import sys

    # DEBUG: Print Python path info
    print(f"[DEBUG] Python executable: {sys.executable}")
    print(f"[DEBUG] Python version: {sys.version}")
    print(f"[DEBUG] sys.path has {len(sys.path)} entries")

    try:
        from langchain_groq import ChatGroq
        print(f"[DEBUG] Successfully imported ChatGroq")
    except ImportError as e:
        print(f"[DEBUG] Failed to import langchain_groq: {e}")
        print(f"[DEBUG] sys.path: {sys.path[:3]}")  # Show first 3 paths
        raise ImportError(
            "langchain-groq is required for Groq support. "
            "Install with: pip install langchain-groq"
        )

    # Validate API key - check both config and os.getenv
    api_key = config.GROQ_API_KEY or os.getenv('GROQ_API_KEY')

    if not api_key:
        raise ValueError(
            "GROQ_API_KEY environment variable is not set. "
            "Get your FREE API key at: https://console.groq.com/keys "
            "Then set it with: export GROQ_API_KEY='your-api-key' (Linux/Mac) "
            "or set GROQ_API_KEY=your-api-key (Windows)"
        )

    return ChatGroq(
        model=model or config.GROQ_MODEL,
        groq_api_key=api_key,
        temperature=temperature or config.GROQ_TEMPERATURE,
        max_tokens=max_tokens or config.GROQ_MAX_TOKENS
    )


def _get_gemini_llm(model=None, temperature=None, max_tokens=None):
    """Initialize Google Gemini LLM (BACKUP - only 20 requests/day)."""
    import os

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except ImportError:
        raise ImportError(
            "langchain-google-genai is required for Gemini support. "
            "Install with: pip install langchain-google-genai"
        )

    # Validate API key - check both config and os.getenv
    api_key = config.GEMINI_API_KEY or os.getenv('GEMINI_API_KEY')

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Set it with: export GEMINI_API_KEY='your-api-key' (Linux/Mac) "
            "or set GEMINI_API_KEY=your-api-key (Windows)"
        )

    return ChatGoogleGenerativeAI(
        model=model or config.GEMINI_MODEL,
        google_api_key=api_key,
        temperature=temperature or config.GEMINI_TEMPERATURE,
        max_output_tokens=max_tokens or config.GEMINI_MAX_OUTPUT_TOKENS,
        convert_system_message_to_human=True  # Gemini compatibility
    )


def _get_ollama_llm(model=None, temperature=None, max_tokens=None):
    """Initialize Ollama LLM (DEPRECATED)."""
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        raise ImportError(
            "langchain-ollama is required for Ollama support. "
            "Install with: pip install langchain-ollama"
        )

    return ChatOllama(
        model=config.OLLAMA_MODEL if hasattr(config, 'OLLAMA_MODEL') else "llama3.2",
        base_url=config.OLLAMA_BASE_URL if hasattr(config, 'OLLAMA_BASE_URL') else "http://localhost:11434",
        temperature=temperature or 0.7
    )


def validate_llm_setup() -> dict:
    """
    Validate LLM configuration.

    Returns:
        Dictionary with validation results
    """
    import os

    validation = {
        "provider": config.LLM_PROVIDER,
        "ready": False,
        "errors": []
    }

    # DEBUG: Print what we see
    print(f"[DEBUG] validate_llm_setup called")
    print(f"[DEBUG] Current dir: {os.getcwd()}")
    print(f"[DEBUG] config.GROQ_API_KEY: {'SET' if config.GROQ_API_KEY else 'NOT SET'}")
    print(f"[DEBUG] os.getenv('GROQ_API_KEY'): {'SET' if os.getenv('GROQ_API_KEY') else 'NOT SET'}")

    if config.LLM_PROVIDER == "groq":
        # Check both config and os.getenv as fallback
        api_key = config.GROQ_API_KEY or os.getenv('GROQ_API_KEY')

        if not api_key:
            validation["errors"].append("GROQ_API_KEY environment variable not set. Get your FREE API key at: https://console.groq.com/keys")
            print(f"[DEBUG] Groq API key NOT found")
        else:
            validation["ready"] = True
            validation["model"] = config.GROQ_MODEL
            print(f"[DEBUG] Groq API key found: {api_key[:15]}...")
    elif config.LLM_PROVIDER == "gemini":
        # Check both config and os.getenv as fallback
        api_key = config.GEMINI_API_KEY or os.getenv('GEMINI_API_KEY')

        if not api_key:
            validation["errors"].append("GEMINI_API_KEY environment variable not set")
            print(f"[DEBUG] Gemini API key NOT found")
        else:
            validation["ready"] = True
            validation["model"] = config.GEMINI_MODEL
            print(f"[DEBUG] Gemini API key found: {api_key[:15]}...")
    elif config.LLM_PROVIDER == "ollama":
        validation["ready"] = True
        validation["model"] = config.OLLAMA_MODEL if hasattr(config, 'OLLAMA_MODEL') else "llama3.2"
        validation["errors"].append("Ollama is deprecated. Please switch to Groq or Gemini.")
    else:
        validation["errors"].append(f"Unknown provider: {config.LLM_PROVIDER}")

    print(f"[DEBUG] Validation result: ready={validation['ready']}, errors={validation['errors']}")

    return validation
