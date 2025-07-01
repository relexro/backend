"""
Direct Gemini API Utilities - Use google.generativeai directly (bypassing LangChain)
"""
import os
import logging
from typing import Optional, Dict, Any, List
import requests
import asyncio

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # Will raise in function if used without install

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper: Initialize Gemini client
_gemini_client = None

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

def get_gemini_client(api_key: Optional[str] = None):
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    if genai is None:
        raise ImportError("google-generativeai is not installed. Please install it via pip.")
    api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable must be set.")
    genai.configure(api_key=api_key)
    _gemini_client = genai
    return _gemini_client

async def gemini_generate(
    prompt: str,
    model_name: str = "gemini-pro",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    api_key: Optional[str] = None,
    **kwargs
) -> str:
    """
    Generate content using Gemini API directly (bypassing LangChain).
    Args:
        prompt: The prompt string to send to Gemini
        model_name: Gemini model to use (default: gemini-pro)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        api_key: Optional API key override
        kwargs: Additional parameters for the model
    Returns:
        The generated text response
    """
    client = get_gemini_client(api_key)
    try:
        # The official SDK is sync, so run in thread executor for async compatibility
        loop = asyncio.get_event_loop()
        model = client.GenerativeModel(model_name)
        def _run():
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
                **kwargs
            )
            return response.text if hasattr(response, "text") else str(response)
        return await loop.run_in_executor(None, _run)
    except Exception as e:
        logger.error(f"Error in direct Gemini API call: {str(e)}")
        raise 

async def gemini_generate_rest(
    prompt: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
    temperature: float = 1.0,
    top_p: float = 0.95,
    candidate_count: int = 1,
    max_tokens: int = 256,
    api_key: Optional[str] = None,
    contents: Optional[List[Dict[str, Any]]] = None,
    system_prompt: Optional[str] = None,
    user_prompt: Optional[str] = None,
    **kwargs
) -> str:
    """
    Generate content using Gemini API via direct REST call (bypassing SDK).
    Args:
        prompt: (legacy) The prompt string to send to Gemini (used if contents is not provided).
        model_name: The Gemini model to use (e.g., 'gemini-2.5-flash').
        temperature: Sampling temperature (default 1.0).
        top_p: Nucleus sampling probability (default 0.95).
        candidate_count: Number of candidates to generate (default 1).
        max_tokens: Maximum output tokens (default 256).
        api_key: Gemini API key (default: from env var GEMINI_API_KEY).
        contents: List of dicts, each with 'role' and 'parts', for multi-role/multi-part prompts.
        system_prompt: If provided, used as the first 'system' part (if contents is not set).
        user_prompt: If provided, used as the first 'user' part (if contents is not set).
        kwargs: Additional generationConfig parameters.
    Returns:
        The generated text (str).
    """
    if api_key is None:
        api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment or passed explicitly.")

    url = GEMINI_API_URL.format(model=model_name)
    headers = {"Content-Type": "application/json"}
    # Build generationConfig with sensible defaults, allow override via kwargs
    generation_config = {
        "temperature": temperature,
        "topP": top_p,
        "candidateCount": candidate_count,
        "maxOutputTokens": max_tokens,
    }
    generation_config.update(kwargs)

    # Build contents: prefer explicit, else fallback to system/user/prompt
    if contents is not None:
        payload_contents = contents
    elif system_prompt or user_prompt:
        payload_contents = []
        if system_prompt:
            payload_contents.append({"role": "system", "parts": [{"text": system_prompt}]})
        if user_prompt:
            payload_contents.append({"role": "user", "parts": [{"text": user_prompt}]})
    elif prompt:
        payload_contents = [{"role": "user", "parts": [{"text": prompt}]}]
    else:
        raise ValueError("You must provide either contents, or system_prompt/user_prompt, or prompt.")

    payload = {
        "contents": payload_contents,
        "generationConfig": generation_config
    }
    def _post():
        response = requests.post(f"{url}?key={api_key}", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        print("Gemini API raw response:", data)
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except KeyError:
            print("Candidate content:", data["candidates"][0]["content"])
            return str(data["candidates"][0]["content"])
        except Exception as e:
            logger.error(f"Malformed Gemini API response: {data}")
            raise RuntimeError(f"Malformed Gemini API response: {e}")
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _post) 