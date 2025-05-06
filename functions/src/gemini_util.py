"""
Gemini API Utilities - Helper functions for using Google's Gemini API
"""
import os
import logging
import google.generativeai as genai
from typing import Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up the Gemini API client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    logger.info("Using GEMINI_API_KEY from environment variables")
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY is not set. Gemini functionality will not work.")

def create_gemini_model(model_name: str = "gemini-pro") -> Any:
    """
    Create and configure a Gemini model with the given model name.
    
    Args:
        model_name: The model name to use. Default is "gemini-pro".
        
    Returns:
        A configured Gemini model object.
    """
    try:
        # Initialize the model
        model = genai.GenerativeModel(model_name)
        logger.info(f"Successfully initialized Gemini model {model_name}")
        return model
    except Exception as e:
        logger.error(f"Error initializing Gemini model: {str(e)}")
        raise RuntimeError(f"Failed to initialize Gemini model: {str(e)}")

def analyze_gemini_response(response: Any, analysis_type: str) -> Dict[str, Any]:
    """
    Process the response from Gemini and extract structured data.
    
    Args:
        response: The raw response from Gemini
        analysis_type: The type of analysis being performed (for logging)
        
    Returns:
        Extracted structured data from the response
    """
    try:
        if not response.text:
            raise ValueError("Empty response from Gemini API")
            
        # Basic preprocessing to handle different response formats
        text = response.text.strip()
        
        # Try to extract JSON from the response if it contains JSON blocks
        result = {}
        
        # For now, just return the raw text as the response
        # In a production environment, this would be more sophisticated
        result = {
            "full_text": text,
            "analysis_type": analysis_type,
            "status": "success"
        }
            
        # Add other fields based on analysis type
        if analysis_type == "legal_analysis":
            # Simple placeholder - in production, this would use a more robust extraction method
            result["domains"] = {"main": "civil"}
            result["keywords"] = ["contract", "agreement"]
            result["complexity"] = {"level": 2, "reasoning": "Complex legal situation"}
            
        logger.info(f"Successfully processed {analysis_type} response")
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing Gemini response: {str(e)}")
        # Return a basic error result
        return {
            "status": "error",
            "error": str(e),
            "analysis_type": analysis_type
        } 