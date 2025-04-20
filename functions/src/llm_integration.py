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

from langchain_google_genai import ChatGoogleGenerativeAI
from custom_grok_client import GrokClient

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
    
    async def initialize(self) -> None:
        """Initialize the Gemini model."""
        try:
            self.model = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                max_output_tokens=self.max_tokens
            )
        except Exception as e:
            logger.error(f"Error initializing Gemini: {str(e)}")
            raise LLMError(f"Eroare la inițializarea Gemini: {str(e)}")

@dataclass
class GrokProcessor:
    """Processor for Grok model integration."""
    model_name: str
    temperature: float
    max_tokens: int
    
    async def initialize(self) -> None:
        """Initialize the Grok model."""
        try:
            self.model = GrokClient(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
        except Exception as e:
            logger.error(f"Error initializing Grok: {str(e)}")
            raise LLMError(f"Eroare la inițializarea Grok: {str(e)}")

def prepare_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare context for LLM processing."""
    prepared_context = {
        "timestamp": datetime.now().isoformat(),
        "language": "ro",  # Romanian language
    }
    
    # Add available context fields
    if "case_type" in context:
        prepared_context["case_type"] = context["case_type"]
    if "parties" in context:
        prepared_context["parties"] = context["parties"]
    if "legal_basis" in context:
        prepared_context["legal_basis"] = [
            str(basis) for basis in context["legal_basis"]
        ]
    if "precedents" in context:
        prepared_context["precedents"] = context["precedents"]
    if "claim_value" in context:
        prepared_context["claim_value"] = float(context["claim_value"])
    
    return prepared_context

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
            messages=[{"role": "user", "content": full_prompt}]
        )
        
        if not response or not response[0].content:
            raise LLMError("Nu s-a primit niciun răspuns de la Gemini")
        
        return response[0].content
        
    except Exception as e:
        logger.error(f"Error in Gemini processing: {str(e)}")
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

async def process_legal_query(
    context: Dict[str, Any],
    query: str,
    session_id: Optional[str] = None
) -> Dict[str, Any]:
    """Process a legal query using both Gemini and Grok."""
    try:
        # Initialize processors
        gemini = GeminiProcessor(
            model_name="gemini-pro",
            temperature=0.7,
            max_tokens=2048
        )
        grok = GrokProcessor(
            model_name="grok-1",
            temperature=0.8,
            max_tokens=4096
        )
        
        # Get initial analysis from Gemini
        initial_analysis = await process_with_gemini(
            gemini,
            context,
            "Analizează aspectele juridice principale ale cazului și identifică legislația relevantă."
        )
        
        # Enhanced context with Gemini's analysis
        enhanced_context = {
            **context,
            "preliminary_analysis": initial_analysis
        }
        
        # Get expert recommendations from Grok
        expert_recommendations = await process_with_grok(
            grok,
            enhanced_context,
            f"Bazat pe analiza preliminară și contextul dat, {query}"
        )
        
        return {
            "initial_analysis": initial_analysis,
            "expert_recommendations": expert_recommendations,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in legal query processing: {str(e)}")
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": datetime.now().isoformat()
        }

async def maintain_conversation_history(
    session_id: str,
    role: str,
    content: str,
    history: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """Maintain conversation history for a session."""
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    
    # Keep only last 10 messages to manage context window
    if len(history) > 10:
        history = history[-10:]
    
    return history 