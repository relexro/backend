"""
Gemini API Utilities - Helper functions for using Google's Gemini API
"""
import os
import logging
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Alias kept for older import paths
genai = None  # type: ignore  # noqa: E701

# ---------------------------------------------------------------------------
# Helper wrappers to mirror the previous interface but delegate to LangChain
# ---------------------------------------------------------------------------

class _GeminiAsyncWrapper:
    """Provide the old `generate_content_async` coroutine expected by agent nodes."""

    def __init__(self, model: ChatGoogleGenerativeAI):
        self._model = model

    async def generate_content_async(self, system_prompt: str, user_message: str, *_args, **_kw):  # type: ignore
        # Combine system and user prompt similar to old helper
        prompt = f"{system_prompt}\n\n{user_message}"
        return await self._model.ainvoke([HumanMessage(content=prompt)])


def create_gemini_model(model_name: str = "gemini-pro", temperature: float = 0.7, max_tokens: int = 2048) -> _GeminiAsyncWrapper:
    """Return a wrapper around ChatGoogleGenerativeAI matching the previous util API."""
    api_key = os.getenv("GEMINI_API_KEY")
    model = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        max_output_tokens=max_tokens,
        google_api_key=api_key,
    )
    return _GeminiAsyncWrapper(model)


def analyze_gemini_response(response: Any, analysis_type: str) -> Dict[str, Any]:
    """Basic pass-through analysis compatible with previous tests."""
    try:
        text = getattr(response, "content", "").strip()
        if not text:
            raise ValueError("Empty response from Gemini")

        result: Dict[str, Any] = {
            "full_text": text,
            "analysis_type": analysis_type,
            "status": "success",
        }
        return result
    except Exception as e:
        logging.error(f"Error analyzing Gemini response: {str(e)}")
        return {"status": "error", "error": str(e), "analysis_type": analysis_type} 