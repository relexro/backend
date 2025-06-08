"""
Custom Grok Client for Relex Legal Assistant
"""
from typing import Optional, Dict, Any
import aiohttp
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GrokClient:
    """Client for interacting with the Grok API."""
    
    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ):
        """
        Initialize the Grok client.
        
        Args:
            model: The model name to use
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = os.environ.get('GROK_API_KEY')
        if not self.api_key:
            logger.warning("GROK_API_KEY not found in environment variables")
        
    async def generate(
        self,
        prompt: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a response from the Grok model.
        
        Args:
            prompt: The input prompt
            session_id: Optional session ID for conversation context
            
        Returns:
            Dictionary containing the response
        """
        if not self.api_key:
            raise ValueError("GROK_API_KEY environment variable is required")
            
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
                
                if session_id:
                    data["session_id"] = session_id
                
                async with session.post(
                    "https://api.grok.ai/v1/generate",
                    headers=headers,
                    json=data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API error: {error_text}")
                        
                    result = await response.json()
                    return {
                        "content": result.get("text", ""),
                        "usage": result.get("usage", {}),
                        "finish_reason": result.get("finish_reason")
                    }
                    
        except Exception as e:
            logger.error(f"Error in Grok API call: {str(e)}")
            raise Exception(f"Failed to generate response: {str(e)}") 