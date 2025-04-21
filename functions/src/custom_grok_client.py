"""
Custom Grok Client for Relex Legal Assistant
"""
import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Import the grok_client package
try:
    from grok_client import GrokAPI
except ImportError:
    logging.warning("grok_client package not found. Using mock implementation.")
    GrokAPI = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class GrokResponse:
    """Response from Grok API."""
    content: str
    metadata: Dict[str, Any] = None

class GrokClient:
    """Client for interacting with Grok API."""
    
    def __init__(self, model: str = "grok-1", temperature: float = 0.7, max_tokens: int = 4096):
        """Initialize the Grok client.
        
        Args:
            model: The model name to use
            temperature: The temperature for generation
            max_tokens: The maximum number of tokens to generate
        """
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Get API key from environment variable
        self.api_key = os.environ.get("GROK_API_KEY")
        
        if not self.api_key:
            logger.warning("GROK_API_KEY environment variable not set")
            self.client = None
        elif GrokAPI is None:
            logger.warning("GrokAPI not available, using mock implementation")
            self.client = None
        else:
            try:
                self.client = GrokAPI(api_key=self.api_key)
                logger.info(f"Initialized Grok client with model {model}")
            except Exception as e:
                logger.error(f"Error initializing Grok client: {str(e)}")
                self.client = None
    
    async def generate(self, prompt: str, session_id: Optional[str] = None) -> GrokResponse:
        """Generate a response from Grok.
        
        Args:
            prompt: The prompt to send to Grok
            session_id: Optional session ID for conversation tracking
            
        Returns:
            GrokResponse object with content and metadata
        """
        if not self.client:
            logger.warning("Using mock Grok response because client is not initialized")
            return self._mock_response(prompt)
        
        try:
            # Call the Grok API
            response = self.client.chat_completions(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Extract the response content
            if response and response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                return GrokResponse(content=content, metadata={"model": self.model})
            else:
                logger.error("Empty or invalid response from Grok API")
                return GrokResponse(content="Nu am putut genera un răspuns valid.", 
                                   metadata={"error": "empty_response"})
                
        except Exception as e:
            logger.error(f"Error generating response from Grok: {str(e)}")
            return GrokResponse(content=f"Eroare la generarea răspunsului: {str(e)}",
                               metadata={"error": str(e)})
    
    def _mock_response(self, prompt: str) -> GrokResponse:
        """Generate a mock response when the API is not available.
        
        Args:
            prompt: The prompt that would have been sent to Grok
            
        Returns:
            GrokResponse with mock content
        """
        return GrokResponse(
            content=(
                "Aceasta este o implementare simulată a Grok API. "
                "API-ul real nu este disponibil sau nu este configurat corect. "
                "Vă rugăm să verificați configurarea API_KEY și conexiunea la internet."
            ),
            metadata={"mock": True, "prompt_length": len(prompt)}
        )
