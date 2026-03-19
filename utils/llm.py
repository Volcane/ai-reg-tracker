"""
ARIS — LLM Provider Abstraction

Single call surface for all agent → LLM interactions. Every agent calls
`call_llm()` instead of touching the Anthropic SDK directly. Provider,
model, and endpoint are all controlled by environment variables, so
switching providers requires only a config change, not a code change.

Supported providers
-------------------
  anthropic   Claude via the Anthropic API (default)
  openai      OpenAI GPT models, or any OpenAI-compatible endpoint
              (Groq, Together AI, Mistral, LM Studio, vLLM, etc.)
  ollama      Fully local models via Ollama (no API key)
  gemini      Google Gemini via the google-generativeai SDK

Configuration (config/keys.env)
---------------------------------
  LLM_PROVIDER   = anthropic          # anthropic | openai | ollama | gemini
  LLM_MODEL      =                    # leave blank for provider default
  LLM_BASE_URL   =                    # for openai-compatible or custom Ollama host
  ANTHROPIC_API_KEY = ...
  OPENAI_API_KEY    = ...
  GEMINI_API_KEY    = ...

Provider defaults
-----------------
  anthropic  →  claude-sonnet-4-20250514
  openai     →  gpt-4o
  ollama     →  llama3.1  (run: ollama pull llama3.1)
  gemini     →  gemini-1.5-pro

OpenAI-compatible endpoints (set LLM_PROVIDER=openai and LLM_BASE_URL):
  Groq        →  https://api.groq.com/openai/v1       (LLM_MODEL=llama-3.1-70b-versatile)
  Together AI →  https://api.together.xyz/v1          (LLM_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo)
  Mistral     →  https://api.mistral.ai/v1            (LLM_MODEL=mistral-large-latest)
  LM Studio   →  http://localhost:1234/v1             (LLM_MODEL=loaded-model-name)
  vLLM        →  http://localhost:8000/v1             (LLM_MODEL=model-name)

Prompt notes
------------
ARIS prompts ask for JSON with specific field names and use structured
instruction blocks. Strong models (GPT-4o, Gemini 1.5 Pro, Llama 3.1 70B+,
Mixtral 8x22B) follow these reliably. Smaller models (<13B parameters) may
produce malformed JSON more often. The _safe_parse_json helpers in each agent
handle partial failures gracefully.
"""

from __future__ import annotations

import os
from typing import Optional

from utils.cache import get_logger

log = get_logger("aris.llm")

# ── Configuration ─────────────────────────────────────────────────────────────

# These are read fresh each call so they pick up env changes in tests;
# in production they are stable after startup.
def _provider()  -> str: return os.getenv("LLM_PROVIDER",  "anthropic").lower().strip()
def _model()     -> str: return os.getenv("LLM_MODEL",     "").strip()
def _base_url()  -> str: return os.getenv("LLM_BASE_URL",  "").strip()

PROVIDER_DEFAULTS = {
    "anthropic": "claude-sonnet-4-20250514",
    "openai":    "gpt-4o",
    "ollama":    "llama3.1",
    "gemini":    "gemini-1.5-pro",
}

# ── Public interface ──────────────────────────────────────────────────────────

def call_llm(prompt:     str,
             system:     str = "",
             max_tokens: int = 2048) -> str:
    """
    Send a prompt to the configured LLM and return the response text.

    Args:
        prompt:     The user message / instruction.
        system:     Optional system prompt (role instructions / output format).
        max_tokens: Maximum tokens to generate.

    Returns:
        Raw response text (not parsed). Each agent is responsible for
        parsing the text as JSON or extracting the relevant content.

    Raises:
        LLMError: Wraps provider-specific exceptions with a uniform message.
    """
    provider = _provider()
    try:
        if provider == "anthropic":
            return _call_anthropic(prompt, system, max_tokens)
        elif provider == "openai":
            return _call_openai(prompt, system, max_tokens)
        elif provider == "ollama":
            return _call_ollama(prompt, system, max_tokens)
        elif provider == "gemini":
            return _call_gemini(prompt, system, max_tokens)
        else:
            raise LLMError(f"Unknown LLM_PROVIDER '{provider}'. "
                           f"Valid options: anthropic, openai, ollama, gemini")
    except LLMError:
        raise
    except Exception as e:
        raise LLMError(f"[{provider}] {type(e).__name__}: {e}") from e


def is_configured() -> bool:
    """Return True if the current provider has a usable API key / endpoint."""
    provider = _provider()
    if provider == "anthropic":
        return bool(os.getenv("ANTHROPIC_API_KEY", ""))
    elif provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY", "") or _base_url())
    elif provider == "ollama":
        return True   # Ollama has no key; connection checked at call time
    elif provider == "gemini":
        return bool(os.getenv("GEMINI_API_KEY", ""))
    return False


def active_model() -> str:
    """Return the model name that will be used for the current provider."""
    return _model() or PROVIDER_DEFAULTS.get(_provider(), "unknown")


def provider_info() -> dict:
    """Return a dict describing the active LLM configuration (safe to log/display)."""
    p = _provider()
    return {
        "provider":  p,
        "model":     active_model(),
        "base_url":  _base_url() or "(default)",
        "configured":is_configured(),
    }


# ── Provider implementations ──────────────────────────────────────────────────

def _call_anthropic(prompt: str, system: str, max_tokens: int) -> str:
    """Call the Anthropic API using the anthropic SDK."""
    try:
        import anthropic as _anthropic
    except ImportError:
        raise LLMError("anthropic package not installed. Run: pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise LLMError(
            "ANTHROPIC_API_KEY not set. "
            "Get your key at https://console.anthropic.com/settings/keys"
        )

    client  = _anthropic.Anthropic(api_key=api_key)
    model   = _model() or PROVIDER_DEFAULTS["anthropic"]

    kwargs = {
        "model":      model,
        "max_tokens": max_tokens,
        "messages":   [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    try:
        response = client.messages.create(**kwargs)
        return response.content[0].text.strip()
    except _anthropic.APIError as e:
        raise LLMError(f"Anthropic API error: {e}") from e


def _call_openai(prompt: str, system: str, max_tokens: int) -> str:
    """
    Call any OpenAI-compatible API.

    Works with: OpenAI, Groq, Together AI, Mistral, LM Studio, vLLM,
    Ollama's OpenAI-compatible endpoint, and any other provider that
    implements the /chat/completions interface.
    """
    try:
        from openai import OpenAI, APIError as _OAIError
    except ImportError:
        raise LLMError("openai package not installed. Run: pip install openai")

    api_key  = os.getenv("OPENAI_API_KEY", "not-needed-for-local")
    base_url = _base_url() or None
    model    = _model() or PROVIDER_DEFAULTS["openai"]

    client = OpenAI(api_key=api_key, base_url=base_url)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat.completions.create(
            model      = model,
            max_tokens = max_tokens,
            messages   = messages,
        )
        return response.choices[0].message.content.strip()
    except _OAIError as e:
        raise LLMError(f"OpenAI API error: {e}") from e


def _call_ollama(prompt: str, system: str, max_tokens: int) -> str:
    """
    Call a locally running Ollama instance.

    Requires Ollama to be installed and running (https://ollama.com).
    Default host: http://localhost:11434
    Set LLM_BASE_URL to override.
    Set LLM_MODEL to the pulled model name (e.g. llama3.1, mistral, phi3).
    """
    try:
        import requests
    except ImportError:
        raise LLMError("requests package not installed. Run: pip install requests")

    base  = _base_url() or "http://localhost:11434"
    model = _model() or PROVIDER_DEFAULTS["ollama"]

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            f"{base}/api/chat",
            json={
                "model":    model,
                "messages": messages,
                "stream":   False,
                "options":  {"num_predict": max_tokens},
            },
            timeout=120,   # local inference can be slow
        )
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"].strip()
    except Exception as e:
        raise LLMError(
            f"Ollama error at {base}: {e}. "
            f"Is Ollama running? Try: ollama serve"
        ) from e


def _call_gemini(prompt: str, system: str, max_tokens: int) -> str:
    """Call the Google Gemini API via the google-generativeai SDK."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise LLMError(
            "google-generativeai package not installed. "
            "Run: pip install google-generativeai"
        )

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise LLMError(
            "GEMINI_API_KEY not set. "
            "Get your key at https://aistudio.google.com/app/apikey"
        )

    genai.configure(api_key=api_key)
    model_name = _model() or PROVIDER_DEFAULTS["gemini"]

    try:
        model = genai.GenerativeModel(
            model_name          = model_name,
            system_instruction  = system or None,
        )
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(max_output_tokens=max_tokens),
        )
        return response.text.strip()
    except Exception as e:
        raise LLMError(f"Gemini API error: {e}") from e


# ── Exception ─────────────────────────────────────────────────────────────────

class LLMError(Exception):
    """Raised when any LLM provider call fails. Wraps provider-specific exceptions."""
    pass
