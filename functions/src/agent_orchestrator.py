"""
Agent Orchestrator - Defines the agent's workflow graph and state management
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field
from datetime import datetime
import logging
import asyncio
from agent_tools import (
    query_bigquery,
    get_party_id_by_name,
    generate_draft_pdf,
    check_quota,
    get_case_details,
    update_case_details,
    create_support_ticket,
    consult_grok
)

from .template_validation import ValidationError
from .draft_templates import DraftGenerator
from .response_templates import format_response

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class AgentState:
    """Holds all state information for the agent's execution."""
    
    # Case and user information
    case_id: str
    user_id: str
    case_details: Dict[str, Any]
    user_info: Dict[str, Any]
    
    # Execution state
    current_node: str = "start"
    completed_nodes: List[str] = field(default_factory=list)
    execution_start: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Node results
    quota_status: Dict[str, Any] = field(default_factory=dict)
    input_analysis: Dict[str, Any] = field(default_factory=dict)
    research_results: Dict[str, Any] = field(default_factory=dict)
    ai_guidance: Dict[str, Any] = field(default_factory=dict)
    response_data: Dict[str, Any] = field(default_factory=dict)
    
    # Error tracking
    errors: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary format for storage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """Restore state from dictionary format."""
        # Convert string dates back to datetime
        if 'execution_start' in data:
            data['execution_start'] = datetime.fromisoformat(data['execution_start'])
        if 'last_updated' in data:
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)
    
    def update_node(self, node_name: str, result: Dict[str, Any]) -> None:
        """Update state with node execution results."""
        self.current_node = node_name
        self.completed_nodes.append(node_name)
        self.last_updated = datetime.now()
        
        # Store node-specific results
        if node_name == 'check_quota':
            self.quota_status = result
        elif node_name == 'analyze_input':
            self.input_analysis = result
        elif node_name == 'research':
            self.research_results = result
        elif node_name == 'guidance':
            self.ai_guidance = result
        elif node_name == 'generate_response':
            self.response_data = result
    
    def add_error(self, node: str, error: Exception) -> None:
        """Add error information to state."""
        self.errors.append({
            'node': node,
            'error': str(error),
            'timestamp': datetime.now().isoformat()
        })
        self.retry_count[node] = self.retry_count.get(node, 0) + 1

class AgentGraph:
    """Defines and executes the agent's workflow graph."""
    
    def __init__(self):
        self.draft_generator = DraftGenerator()
        self.max_retries = 3
        
        # Define the workflow graph structure
        self.graph = {
            'start': ['check_quota'],
            'check_quota': ['analyze_input'],
            'analyze_input': ['research'],
            'research': ['guidance'],
            'guidance': ['generate_response'],
            'generate_response': ['end']
        }
    
    async def execute(self, state: AgentState) -> Dict[str, Any]:
        """Execute the workflow graph from current state."""
        try:
            current = state.current_node
            while current != 'end':
                logger.info(f"Executing node: {current}")
                
                # Execute current node
                if current == 'check_quota':
                    result = await self._check_quota_node(state)
                elif current == 'analyze_input':
                    result = await self._analyze_input_node(state)
                elif current == 'research':
                    result = await self._research_node(state)
                elif current == 'guidance':
                    result = await self._guidance_node(state)
                elif current == 'generate_response':
                    result = await self._generate_response_node(state)
                else:
                    raise ValueError(f"Unknown node: {current}")
                
                # Update state with results
                state.update_node(current, result)
                
                # Move to next node
                current = self.graph[current][0]
            
            return self._prepare_final_response(state)
            
        except Exception as e:
            logger.error(f"Error in node {current}: {str(e)}")
            state.add_error(current, e)
            
            # Check retry count
            if state.retry_count.get(current, 0) >= self.max_retries:
                await self._create_support_ticket(state)
                raise RuntimeError(f"Max retries exceeded for node {current}")
            
            # Return error response
            return {
                'status': 'error',
                'error': str(e),
                'node': current
            }
    
    async def _check_quota_node(self, state: AgentState) -> Dict[str, Any]:
        """Check user quota and payment status."""
        try:
            # Get user quota information
            quota_info = await self._get_user_quota(state.user_id)
            
            # Check if user has available quota
            if quota_info['available_requests'] <= 0:
                raise ValueError("Insufficient quota")
            
            # Verify payment status if needed
            if quota_info.get('requires_payment'):
                payment_status = await self._verify_payment(state.case_id)
                if not payment_status['paid']:
                    raise ValueError("Payment required")
            
            return {
                'status': 'success',
                'quota': quota_info,
                'payment_verified': True
            }
            
        except Exception as e:
            logger.error(f"Quota check failed: {str(e)}")
            raise
    
    async def _analyze_input_node(self, state: AgentState) -> Dict[str, Any]:
        """Process user input and extract key information."""
        try:
            # Extract names and entities
            names = self._extract_names(state.case_details['input'])
            
            # Build search query
            query = self._build_query(state.case_details['input'])
            
            # Identify document requirements
            doc_types = self._identify_required_documents(state.case_details['input'])
            
            return {
                'status': 'success',
                'names': names,
                'query': query,
                'required_documents': doc_types,
                'context': {
                    'legal_domain': state.case_details.get('legal_domain'),
                    'urgency': state.case_details.get('urgency', 'normal'),
                    'complexity': self._assess_complexity(state.case_details['input'])
                }
            }
            
        except Exception as e:
            logger.error(f"Input analysis failed: {str(e)}")
            raise
    
    async def _research_node(self, state: AgentState) -> Dict[str, Any]:
        """Query legal databases for relevant cases and information."""
        try:
            query = state.input_analysis['query']
            
            # Search legal database
            legal_results = await self._search_legal_database(query)
            
            # Search case law
            case_law = await self._search_case_law(query)
            
            # Get relevant legislation
            legislation = await self._get_relevant_legislation(
                state.input_analysis['context']['legal_domain']
            )
            
            return {
                'status': 'success',
                'legal_references': legal_results,
                'case_law': case_law,
                'legislation': legislation,
                'relevance_scores': self._calculate_relevance(
                    query,
                    legal_results + case_law + legislation
                )
            }
            
        except Exception as e:
            logger.error(f"Legal research failed: {str(e)}")
            raise
    
    async def _guidance_node(self, state: AgentState) -> Dict[str, Any]:
        """Consult Grok for AI guidance on the case."""
        try:
            # Prepare context for Grok
            context = self._prepare_grok_context(state)
            
            # Get Grok guidance
            guidance = await self._get_grok_guidance(context)
            
            # Analyze confidence and risks
            confidence_score = self._analyze_confidence(guidance)
            risks = self._identify_risks(guidance)
            
            return {
                'status': 'success',
                'guidance': guidance,
                'confidence_score': confidence_score,
                'risks': risks,
                'recommendations': self._extract_recommendations(guidance)
            }
            
        except Exception as e:
            logger.error(f"AI guidance failed: {str(e)}")
            raise
    
    async def _generate_response_node(self, state: AgentState) -> Dict[str, Any]:
        """Create final response and optional document drafts."""
        try:
            # Determine if we need to generate drafts
            should_generate_drafts = self._should_generate_drafts(state)
            
            # Prepare response context
            context = self._prepare_response_context(state)
            
            # Generate main response
            response = format_response(
                template_type=state.case_details.get('response_type', 'general_advice'),
                context=context
            )
            
            result = {
                'status': 'success',
                'response': response,
                'confidence_score': state.ai_guidance['confidence_score'],
                'risks': state.ai_guidance['risks']
            }
            
            # Generate drafts if needed
            if should_generate_drafts:
                drafts = []
                for doc_type in state.input_analysis['required_documents']:
                    try:
                        draft = self.draft_generator.generate_draft(
                            draft_type=doc_type,
                            context=self._prepare_draft_context(state, doc_type)
                        )
                        drafts.append(draft)
                    except ValidationError as ve:
                        logger.warning(f"Draft validation failed: {str(ve)}")
                        result['draft_errors'] = result.get('draft_errors', []) + [str(ve)]
                
                result['drafts'] = drafts
            
            return result
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            raise
    
    async def _create_support_ticket(self, state: AgentState) -> None:
        """Create a support ticket for failed execution."""
        try:
            ticket_data = {
                'case_id': state.case_id,
                'user_id': state.user_id,
                'failed_node': state.current_node,
                'errors': state.errors,
                'state_snapshot': state.to_dict()
            }
            
            # Create ticket in support system
            await self._create_ticket(ticket_data)
            
            logger.info(f"Support ticket created for case {state.case_id}")
            
        except Exception as e:
            logger.error(f"Failed to create support ticket: {str(e)}")
    
    def _prepare_final_response(self, state: AgentState) -> Dict[str, Any]:
        """Prepare the final response including all generated content."""
        return {
            'status': 'success',
            'case_id': state.case_id,
            'execution_time': (datetime.now() - state.execution_start).total_seconds(),
            'response': state.response_data.get('response'),
            'drafts': state.response_data.get('drafts', []),
            'confidence_score': state.ai_guidance.get('confidence_score'),
            'risks': state.ai_guidance.get('risks', []),
            'legal_references': state.research_results.get('legal_references', []),
            'metadata': {
                'completed_nodes': state.completed_nodes,
                'errors': state.errors
            }
        }
    
    # Helper methods for node execution
    
    def _extract_names(self, text: str) -> List[str]:
        """Extract names from input text."""
        # TODO: Implement name extraction logic
        return []
    
    def _build_query(self, text: str) -> str:
        """Build search query from input text."""
        # TODO: Implement query building logic
        return text
    
    def _identify_required_documents(self, text: str) -> List[str]:
        """Identify required document types from input."""
        # TODO: Implement document type identification logic
        return []
    
    def _assess_complexity(self, text: str) -> str:
        """Assess the complexity of the legal question."""
        # TODO: Implement complexity assessment logic
        return "medium"
    
    def _calculate_relevance(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate relevance scores for search results."""
        # TODO: Implement relevance calculation logic
        return {}
    
    def _prepare_grok_context(self, state: AgentState) -> Dict[str, Any]:
        """Prepare context for Grok consultation."""
        # TODO: Implement context preparation logic
        return {}
    
    def _analyze_confidence(self, guidance: Dict[str, Any]) -> float:
        """Analyze confidence score from Grok guidance."""
        # TODO: Implement confidence analysis logic
        return 0.8
    
    def _identify_risks(self, guidance: Dict[str, Any]) -> List[str]:
        """Identify potential risks from Grok guidance."""
        # TODO: Implement risk identification logic
        return []
    
    def _extract_recommendations(self, guidance: Dict[str, Any]) -> List[str]:
        """Extract actionable recommendations from Grok guidance."""
        # TODO: Implement recommendation extraction logic
        return []
    
    def _should_generate_drafts(self, state: AgentState) -> bool:
        """Determine if draft generation is needed."""
        return bool(state.input_analysis.get('required_documents'))
    
    def _prepare_response_context(self, state: AgentState) -> Dict[str, Any]:
        """Prepare context for response generation."""
        return {
            'legal_references': state.research_results.get('legal_references', []),
            'case_law': state.research_results.get('case_law', []),
            'legislation': state.research_results.get('legislation', []),
            'recommendations': state.ai_guidance.get('recommendations', []),
            'risks': state.ai_guidance.get('risks', []),
            'confidence_score': state.ai_guidance.get('confidence_score', 0.0)
        }
    
    def _prepare_draft_context(
        self,
        state: AgentState,
        doc_type: str
    ) -> Dict[str, Any]:
        """Prepare context for draft generation."""
        # TODO: Implement draft context preparation logic
        return {}
    
    # External service integration methods
    
    async def _get_user_quota(self, user_id: str) -> Dict[str, Any]:
        """Get user quota information."""
        # TODO: Implement quota checking logic
        return {'available_requests': 10}
    
    async def _verify_payment(self, case_id: str) -> Dict[str, Any]:
        """Verify payment status."""
        # TODO: Implement payment verification logic
        return {'paid': True}
    
    async def _search_legal_database(self, query: str) -> List[Dict[str, Any]]:
        """Search legal database."""
        # TODO: Implement legal database search
        return []
    
    async def _search_case_law(self, query: str) -> List[Dict[str, Any]]:
        """Search case law database."""
        # TODO: Implement case law search
        return []
    
    async def _get_relevant_legislation(self, domain: str) -> List[Dict[str, Any]]:
        """Get relevant legislation."""
        # TODO: Implement legislation lookup
        return []
    
    async def _get_grok_guidance(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get guidance from Grok."""
        # TODO: Implement Grok integration
        return {}
    
    async def _create_ticket(self, ticket_data: Dict[str, Any]) -> None:
        """Create a support ticket."""
        # TODO: Implement support ticket creation
        pass

def create_agent_graph() -> AgentGraph:
    """
    Create and return a new instance of the agent graph.
    """
    return AgentGraph() 