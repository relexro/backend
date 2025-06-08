"""
LLM Integration Module for Relex Legal Assistant
Handles integration with Gemini and Grok models
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import asyncio
import json
import logging
import os
import time

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from custom_grok_client import GrokClient

from functions.src.exceptions import LLMError
from functions.src.utils import prepare_context

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LLMError(Exception):
    """Custom exception for LLM-related errors."""
    pass

@dataclass
class GeminiProcessor:
    """Processor for Gemini model integration."""
    model_name: str
    temperature: float
    max_tokens: int
    model: Optional[ChatGoogleGenerativeAI] = None

    async def initialize(self) -> None:
        """Initialize the Gemini model."""
        try:
            # Get the API key from environment variables
            gemini_api_key = os.environ.get('GEMINI_API_KEY')
            if not gemini_api_key:
                logger.warning("GEMINI_API_KEY not found in environment variables")
                raise ValueError("GEMINI_API_KEY environment variable is required")

            self.model = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens,
                google_api_key=gemini_api_key
            )
            logger.info(f"Successfully initialized Gemini model {self.model_name}")
        except Exception as e:
            logger.error(f"Error initializing Gemini: {str(e)}")
            raise LLMError(f"Eroare la inițializarea Gemini: {str(e)}")

@dataclass
class GrokProcessor:
    """Processor for Grok model integration."""
    model_name: str
    temperature: float
    max_tokens: int
    model: Optional[GrokClient] = None

    async def initialize(self) -> None:
        """Initialize the Grok model."""
        try:
            self.model = GrokClient(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            logger.info(f"Successfully initialized Grok model {self.model_name}")
        except Exception as e:
            logger.error(f"Error initializing Grok: {str(e)}")
            raise LLMError(f"Eroare la inițializarea Grok: {str(e)}")

def format_llm_response(response: Dict[str, Any]) -> str:
    """Format LLM response in Romanian."""
    if "error" in response:
        return f"""
Eroare: {response['error']}
Tip eroare: {response.get('error_type', 'necunoscut')}
"""

    formatted = []

    if "analysis" in response:
        formatted.append(f"Analiză Juridică:\n{response['analysis']}\n")

    if "recommendations" in response:
        formatted.append("Recomandări:\n" + "\n".join(
            f"- {rec}" for rec in response["recommendations"]
        ) + "\n")

    if "risk_factors" in response:
        formatted.append("Factori de Risc:")
        for level, risks in response["risk_factors"].items():
            formatted.append(f"\n{level.upper()}:")
            formatted.extend(f"- {risk}" for risk in risks)

    return "\n".join(formatted)

async def process_with_gemini(
    processor: GeminiProcessor,
    context: Dict[str, Any],
    prompt: str,
    session_id: Optional[str] = None
) -> str:
    """Process request with Gemini."""
    try:
        await processor.initialize()

        prepared_context = prepare_context(context)
        full_prompt = f"""
Context:
{json.dumps(prepared_context, indent=2, ensure_ascii=False)}

Cerere:
{prompt}

Răspunde în limba română, folosind un ton profesional și juridic.
"""

        response = await processor.model.agenerate(
            messages=[HumanMessage(content=full_prompt)],
            generation_config={
                "temperature": processor.temperature,
                "max_output_tokens": processor.max_tokens
            }
        )

        if not response or not response[0].content:
            raise LLMError("Nu s-a primit niciun răspuns de la Gemini")

        return response[0].content

    except Exception as e:
        logger.error(f"Error in Gemini processing: {str(e)}")
        if isinstance(e, LLMError):
            raise
        raise LLMError(f"Eroare la procesarea cu Gemini: {str(e)}")

async def process_with_grok(
    processor: GrokProcessor,
    context: Dict[str, Any],
    prompt: str,
    session_id: Optional[str] = None
) -> str:
    """Process request with Grok."""
    try:
        await processor.initialize()

        prepared_context = prepare_context(context)
        full_prompt = f"""
Context Juridic:
{json.dumps(prepared_context, indent=2, ensure_ascii=False)}

Cerere pentru Analiză Expert:
{prompt}

Oferă o analiză detaliată în limba română, concentrându-te pe:
1. Interpretarea juridică a situației
2. Recomandări specifice bazate pe legislația română
3. Factori de risc și considerații speciale
"""

        response = await processor.model.generate(
            prompt=full_prompt,
            session_id=session_id
        )

        if not response or not response.content:
            raise LLMError("Nu s-a primit niciun răspuns de la Grok")

        return response.content

    except Exception as e:
        logger.error(f"Error in Grok processing: {str(e)}")
        raise LLMError(f"Eroare la procesarea cu Grok: {str(e)}")

async def get_case_details(case_id: str) -> Dict[str, Any]:
    """Get case details from the database."""
    try:
        # TODO: Implement actual database query
        return {
            "case_id": case_id,
            "status": "active",
            "last_update": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting case details: {str(e)}")
        raise LLMError(f"Failed to get case details: {str(e)}")

async def update_case_details(case_id: str, details: Dict[str, Any]) -> None:
    """Update case details in the database."""
    try:
        # TODO: Implement actual database update
        logger.info(f"Updated case {case_id} with details: {details}")
    except Exception as e:
        logger.error(f"Error updating case details: {str(e)}")
        raise LLMError(f"Failed to update case details: {str(e)}")

async def process_legal_query(
    context: Dict[str, Any],
    query: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Process legal query with appropriate model."""
    try:
        if not context:
            raise LLMError("Context cannot be empty")

        # Initialize processors
        gemini_processor = GeminiProcessor(
            model_name="gemini-pro",
            temperature=0.7,
            max_tokens=2048
        )

        grok_processor = GrokProcessor(
            model_name="grok-1",
            temperature=0.8,
            max_tokens=4096
        )

        # Track performance if requested
        start_time = time.time()

        # Process with Gemini first
        try:
            initial_analysis = await process_with_gemini(
                gemini_processor,
                context,
                query,
                session_id
            )
        except LLMError as e:
            if context.get("enable_fallback", False):
                logger.info("Primary model failed, falling back to Grok")
                initial_analysis = await process_with_grok(
                    grok_processor,
                    context,
                    query,
                    session_id
                )
                return {
                    "initial_analysis": initial_analysis,
                    "fallback_model_used": True,
                    "timestamp": datetime.now().isoformat()
                }
            raise

        # For urgent administrative cases, add specific processing
        if context.get("case_type") == "administrative" and context.get("urgency"):
            expert_recommendations = await process_with_grok(
                grok_processor,
                context,
                "Analizează condițiile suspendării actului administrativ și recomandă procedura de urgență",
                session_id
            )
        else:
            expert_recommendations = await process_with_grok(
                grok_processor,
                context,
                query,
                session_id
            )

        result = {
            "initial_analysis": initial_analysis,
            "expert_recommendations": expert_recommendations,
            "timestamp": datetime.now().isoformat()
        }

        # Add performance metrics if requested
        if context.get("track_performance", False):
            result["performance_metrics"] = {
                "total_processing_time": time.time() - start_time,
                "gemini_processing_time": time.time() - start_time,
                "grok_processing_time": time.time() - start_time
            }

        return result

    except Exception as e:
        logger.error(f"Error in legal query processing: {str(e)}")
        raise LLMError(str(e))

async def maintain_conversation_history(
    session_id: str,
    role: str,
    content: str,
    history: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Maintain conversation history for a session."""
    try:
        # Add new message to history
        history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Keep only last 10 messages
        if len(history) > 10:
            history = history[-10:]

        return history

    except Exception as e:
        logger.error(f"Error maintaining conversation history: {str(e)}")
        raise LLMError(f"Failed to maintain conversation history: {str(e)}")