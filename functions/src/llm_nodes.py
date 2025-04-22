"""
LLM Nodes - Specialized nodes for LLM processing with Gemini and Grok
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import logging
import json
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import google.generativeai as genai
from pydantic import BaseModel, Field

# Import agent_tools without circular dependency
from agent_tools import consult_grok

# Define AgentState here to avoid circular import
class AgentState(BaseModel):
    """State management for the legal assistant agent."""

    # Case and user information
    case_id: str
    user_id: str
    case_details: Dict[str, Any] = Field(default_factory=dict)
    user_info: Dict[str, Any] = Field(default_factory=dict)

    # Execution state
    current_node: str = "start"
    completed_nodes: List[str] = Field(default_factory=list)
    retry_count: Dict[str, int] = Field(default_factory=dict)

    # Node results
    quota_status: Dict[str, Any] = Field(default_factory=dict)
    input_analysis: Dict[str, Any] = Field(default_factory=dict)
    research_results: Dict[str, Any] = Field(default_factory=dict)
    ai_guidance: Dict[str, Any] = Field(default_factory=dict)
    response_data: Dict[str, Any] = Field(default_factory=dict)

    # Conversation history
    messages: List[Dict[str, str]] = Field(default_factory=list)

    # Error tracking
    errors: List[Dict[str, Any]] = Field(default_factory=list)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Gemini
GEMINI_MODEL = "gemini-pro"
gemini = ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=0.1)

# System prompts
LEGAL_ANALYSIS_PROMPT = """
You are a Romanian Legal Assistant AI. Your role is to:
1. Analyze legal queries with precision and attention to detail
2. Consider Romanian legal framework and jurisdiction
3. Identify key legal concepts and requirements
4. Maintain professional and formal communication
5. Provide clear, actionable advice
6. Flag high-risk or complex issues for expert review

Respond in Romanian unless specifically asked otherwise.
"""

DOCUMENT_GENERATION_PROMPT = """
You are a Romanian Legal Document Generator AI. Your role is to:
1. Create professional legal documents following Romanian standards
2. Use formal legal language and proper formatting
3. Include all required legal elements and clauses
4. Maintain consistency in terminology
5. Structure documents logically and clearly
6. Add proper headers, footers, and reference numbers

Generate all content in Romanian unless specifically asked otherwise.
"""

async def legal_analysis_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Specialized node for in-depth legal analysis using Gemini.
    """
    try:
        # Prepare conversation history
        messages = [
            SystemMessage(content=LEGAL_ANALYSIS_PROMPT),
            HumanMessage(content=f"""
            Analizeaza urmatoarea situatie juridica:

            Context: {state.case_details.get('input', '')}

            Te rog sa furnizezi:
            1. Domeniul juridic principal si subdomenii relevante
            2. Legislatia aplicabila (coduri, legi, ordonante)
            3. Jurisprudenta relevanta
            4. Riscuri si implicatii juridice
            5. Pasi recomandati de urmat
            6. Nivel de complexitate si urgenta

            Raspunde in format JSON cu urmatoarele campuri:
            {
                "domains": {"main": "", "sub": []},
                "legislation": {"codes": [], "laws": [], "ordinances": []},
                "jurisprudence": [],
                "risks": [],
                "steps": [],
                "complexity": {"level": 1-3, "urgency": "normal/urgent"}
            }
            """)
        ]

        # Get Gemini's analysis
        response = await gemini.ainvoke(messages)
        analysis = json.loads(response.content.strip())

        # Update state
        state.input_analysis.update({
            'legal_analysis': analysis,
            'timestamp': datetime.now().isoformat()
        })
        state.completed_nodes.append('legal_analysis')

        # Add analysis to messages for context
        state.messages.append({
            'role': 'assistant',
            'content': json.dumps(analysis, indent=2, ensure_ascii=False)
        })

        # Determine next node based on complexity
        if analysis['complexity']['level'] >= 2:
            return 'expert_consultation', state
        return 'document_planning', state

    except Exception as e:
        logger.error(f"Error in legal_analysis_node: {str(e)}")
        state.errors.append({
            'node': 'legal_analysis',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state

async def expert_consultation_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Specialized node for consulting Grok on complex legal matters.
    """
    try:
        # Prepare context for Grok
        legal_analysis = state.input_analysis.get('legal_analysis', {})
        context = {
            'query': state.case_details.get('input', ''),
            'domain': legal_analysis.get('domains', {}),
            'legislation': legal_analysis.get('legislation', {}),
            'complexity': legal_analysis.get('complexity', {}),
            'risks': legal_analysis.get('risks', [])
        }

        # Get Grok's expert guidance
        guidance = await consult_grok(
            state.case_id,
            context,
            specific_question="""
            Based on the legal analysis provided, please:
            1. Validate or correct the identified legal framework
            2. Provide strategic guidance for handling the case
            3. Identify any additional risks or considerations
            4. Suggest specific precedents or doctrine to reference
            5. Recommend optimal approach for document preparation
            """
        )

        # Update state
        state.ai_guidance = {
            'expert_consultation': guidance,
            'timestamp': datetime.now().isoformat()
        }
        state.completed_nodes.append('expert_consultation')

        # Add guidance to messages
        state.messages.append({
            'role': 'assistant',
            'content': f"Expert Guidance:\n{guidance['recommendations']}"
        })

        return 'document_planning', state

    except Exception as e:
        logger.error(f"Error in expert_consultation_node: {str(e)}")
        state.errors.append({
            'node': 'expert_consultation',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state

async def document_planning_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Specialized node for planning document generation using Gemini.
    """
    try:
        # Prepare conversation history
        messages = [
            SystemMessage(content=DOCUMENT_GENERATION_PROMPT),
            HumanMessage(content=f"""
            Planifica generarea documentelor pentru urmatoarea situatie:

            Context: {state.case_details.get('input', '')}
            Analiza: {json.dumps(state.input_analysis.get('legal_analysis', {}), ensure_ascii=False)}
            Recomandari Expert: {json.dumps(state.ai_guidance.get('expert_consultation', {}), ensure_ascii=False)}

            Pentru fiecare document necesar, specifica:
            1. Tipul documentului
            2. Structura si sectiuni
            3. Referinte legislative necesare
            4. Date si informatii necesare
            5. Nivel de prioritate

            Raspunde in format JSON cu urmatoarea structura:
            {
                "documents": [
                    {
                        "type": "",
                        "structure": [],
                        "legal_refs": [],
                        "required_data": [],
                        "priority": "high/medium/low"
                    }
                ]
            }
            """)
        ]

        # Get Gemini's plan
        response = await gemini.ainvoke(messages)
        doc_plan = json.loads(response.content.strip())

        # Update state
        state.response_data.update({
            'document_plan': doc_plan,
            'timestamp': datetime.now().isoformat()
        })
        state.completed_nodes.append('document_planning')

        # Add plan to messages
        state.messages.append({
            'role': 'assistant',
            'content': json.dumps(doc_plan, indent=2, ensure_ascii=False)
        })

        return 'generate_documents', state

    except Exception as e:
        logger.error(f"Error in document_planning_node: {str(e)}")
        state.errors.append({
            'node': 'document_planning',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state

async def document_generation_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Specialized node for generating legal documents using Gemini.
    """
    try:
        documents = []
        doc_plan = state.response_data.get('document_plan', {}).get('documents', [])

        for doc in doc_plan:
            # Prepare document context
            messages = [
                SystemMessage(content=DOCUMENT_GENERATION_PROMPT),
                HumanMessage(content=f"""
                Genereaza continutul pentru urmatorul document juridic:

                Tip Document: {doc['type']}
                Structura: {json.dumps(doc['structure'], ensure_ascii=False)}
                Referinte Legislative: {json.dumps(doc['legal_refs'], ensure_ascii=False)}

                Context:
                {state.case_details.get('input', '')}

                Analiza Juridica:
                {json.dumps(state.input_analysis.get('legal_analysis', {}), ensure_ascii=False)}

                Recomandari Expert:
                {json.dumps(state.ai_guidance.get('expert_consultation', {}), ensure_ascii=False)}

                Genereaza documentul in format Markdown, respectand structura specificata.
                Include toate elementele necesare (antet, numar, data, semnaturi etc).
                """)
            ]

            # Generate document content
            response = await gemini.ainvoke(messages)
            content = response.content.strip()

            # Add to documents list
            documents.append({
                'type': doc['type'],
                'content': content,
                'metadata': {
                    'structure': doc['structure'],
                    'legal_refs': doc['legal_refs'],
                    'priority': doc['priority']
                }
            })

        # Update state
        state.response_data.update({
            'generated_documents': documents,
            'timestamp': datetime.now().isoformat()
        })
        state.completed_nodes.append('generate_documents')

        return 'final_review', state

    except Exception as e:
        logger.error(f"Error in document_generation_node: {str(e)}")
        state.errors.append({
            'node': 'generate_documents',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state

async def final_review_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Specialized node for final review and quality check using both Gemini and Grok.
    """
    try:
        # First, get Gemini's review
        messages = [
            SystemMessage(content=LEGAL_ANALYSIS_PROMPT),
            HumanMessage(content=f"""
            Revizuieste urmatorul pachet de documente si raspuns:

            Raspuns General:
            {state.response_data.get('response', '')}

            Documente Generate:
            {json.dumps(state.response_data.get('generated_documents', []), ensure_ascii=False)}

            Verifica:
            1. Acuratetea juridica
            2. Completitudinea documentelor
            3. Consistenta terminologiei
            4. Claritatea explicatiilor
            5. Referintele legislative

            Raspunde cu un JSON continand:
            {
                "accuracy_score": 0-100,
                "completeness_score": 0-100,
                "consistency_score": 0-100,
                "clarity_score": 0-100,
                "issues": [],
                "recommendations": []
            }
            """)
        ]

        # Get Gemini's review
        response = await gemini.ainvoke(messages)
        review = json.loads(response.content.strip())

        # If any score is below 90, get Grok's review
        if any(review.get(f"{metric}_score", 0) < 90 for metric in ["accuracy", "completeness", "consistency", "clarity"]):
            grok_review = await consult_grok(
                state.case_id,
                {
                    'initial_review': review,
                    'response_data': state.response_data
                },
                specific_question="Please review the generated response and documents for legal accuracy and completeness."
            )

            # Update review with Grok's input
            review['expert_review'] = grok_review

        # Update state
        state.response_data.update({
            'quality_review': review,
            'final_timestamp': datetime.now().isoformat()
        })
        state.completed_nodes.append('final_review')

        return 'end', state

    except Exception as e:
        logger.error(f"Error in final_review_node: {str(e)}")
        state.errors.append({
            'node': 'final_review',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state