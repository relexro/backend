"""
Gemini API Utilities - Helper functions for using Google's Gemini API
"""
import os
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_gemini_model(model_name: str = "gemini-pro", temperature: float = 0.7, max_tokens: int = 2048):
    # This function is now obsolete; use direct Gemini API implementation instead.
    raise NotImplementedError("create_gemini_model is obsolete. Use direct Gemini API implementation.")


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


def build_gemini_contents(
    system_prompt: str,
    user_message: str,
    enriched_prompt: str = None,
    tool_outputs: list = None,
    grok_output: str = None
) -> list:
    """
    Build the Gemini API 'contents' list for a multi-part, multi-role prompt.
    Args:
        system_prompt: The main system prompt (from agent config)
        user_message: The user's input or case details
        enriched_prompt: Optional, case-type-specific enriched prompt
        tool_outputs: Optional, list of tool outputs (as strings)
        grok_output: Optional, Grok's expert output (as string)
    Returns:
        List of dicts for Gemini API 'contents' param
    """
    contents = []
    if system_prompt:
        contents.append({"role": "system", "parts": [{"text": system_prompt}]})
    if enriched_prompt:
        contents.append({"role": "system", "parts": [{"text": enriched_prompt}]})
    if user_message:
        contents.append({"role": "user", "parts": [{"text": user_message}]})
    if tool_outputs:
        for output in tool_outputs:
            contents.append({"role": "tool", "parts": [{"text": output}]})
    if grok_output:
        contents.append({"role": "assistant", "parts": [{"text": grok_output}]})
    return contents 