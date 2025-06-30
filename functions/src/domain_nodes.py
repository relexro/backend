"""
Domain-specific Nodes - Specialized nodes for different legal domains
"""
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import logging
from pydantic import BaseModel, Field

from agent_nodes import AgentState
from llm_nodes import (
    legal_analysis_node,
    expert_consultation_node
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Domain-specific validation rules
DOMAIN_VALIDATORS = {
    'civil': {
        'required_fields': ['parties', 'claim_value', 'jurisdiction'],
        'document_types': ['cerere_chemare_judecata', 'intampinare', 'concluzii_scrise'],
        'complexity_factors': ['multiple_parties', 'international_elements', 'precedent_cases']
    },
    'commercial': {
        'required_fields': ['company_details', 'contract_value', 'business_domain'],
        'document_types': ['contract_comercial', 'notificare_plata', 'cerere_arbitraj'],
        'complexity_factors': ['multiple_jurisdictions', 'regulatory_compliance', 'industry_specific']
    },
    'administrative': {
        'required_fields': ['authority', 'decision_details', 'legal_basis'],
        'document_types': ['contestatie_administrativa', 'cerere_anulare', 'cerere_suspendare'],
        'complexity_factors': ['public_interest', 'urgency', 'precedent_impact']
    },
    'labor': {
        'required_fields': ['employer', 'employee', 'contract_type'],
        'document_types': ['contestatie_decizie', 'cerere_drepturi_salariale', 'plangere_itm'],
        'complexity_factors': ['collective_aspects', 'discrimination', 'workplace_safety']
    }
}

async def civil_law_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Specialized node for civil law cases.
    """
    try:
        # Validate required fields
        analysis = state.input_analysis.get('legal_analysis', {})
        missing_fields = [
            field for field in DOMAIN_VALIDATORS['civil']['required_fields']
            if not analysis.get(field)
        ]
        
        if missing_fields:
            state.errors.append({
                'node': 'civil_law',
                'error': f'Câmpuri obligatorii lipsă: {", ".join(missing_fields)}',
                'timestamp': datetime.now().isoformat()
            })
            return 'error', state
        
        # Check complexity factors
        complexity_score = sum(
            1 for factor in DOMAIN_VALIDATORS['civil']['complexity_factors']
            if analysis.get(factor, False)
        )
        
        # Update state with domain-specific data
        state.input_analysis.update({
            'domain_specific': {
                'type': 'civil',
                'complexity_score': complexity_score,
                'required_documents': [
                    doc for doc in DOMAIN_VALIDATORS['civil']['document_types']
                    if analysis.get(f'needs_{doc}', False)
                ]
            }
        })
        
        state.completed_nodes.append('civil_law')
        return ('expert_consultation' if complexity_score >= 2 else 'document_planning'), state
        
    except Exception as e:
        logger.error(f"Error in civil_law_node: {str(e)}")
        state.errors.append({
            'node': 'civil_law',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state

async def commercial_law_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Specialized node for commercial law cases.
    """
    try:
        # Validate required fields
        analysis = state.input_analysis.get('legal_analysis', {})
        missing_fields = [
            field for field in DOMAIN_VALIDATORS['commercial']['required_fields']
            if not analysis.get(field)
        ]
        
        if missing_fields:
            state.errors.append({
                'node': 'commercial_law',
                'error': f'Câmpuri obligatorii lipsă: {", ".join(missing_fields)}',
                'timestamp': datetime.now().isoformat()
            })
            return 'error', state
        
        # Check industry-specific requirements
        industry = analysis.get('business_domain', '')
        if industry in ['banking', 'insurance', 'energy']:
            state.input_analysis['regulatory_requirements'] = {
                'industry': industry,
                'special_regulations': True,
                'compliance_needed': True
            }
        
        # Calculate complexity based on contract value
        contract_value = float(analysis.get('contract_value', 0))
        complexity_score = 1
        if contract_value > 1000000:  # 1 million threshold
            complexity_score = 3
        elif contract_value > 100000:  # 100k threshold
            complexity_score = 2
        
        # Update state
        state.input_analysis.update({
            'domain_specific': {
                'type': 'commercial',
                'complexity_score': complexity_score,
                'required_documents': DOMAIN_VALIDATORS['commercial']['document_types']
            }
        })
        
        state.completed_nodes.append('commercial_law')
        return ('expert_consultation' if complexity_score >= 2 else 'document_planning'), state
        
    except Exception as e:
        logger.error(f"Error in commercial_law_node: {str(e)}")
        state.errors.append({
            'node': 'commercial_law',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state

async def administrative_law_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Specialized node for administrative law cases.
    """
    try:
        # Validate required fields
        analysis = state.input_analysis.get('legal_analysis', {})
        missing_fields = [
            field for field in DOMAIN_VALIDATORS['administrative']['required_fields']
            if not analysis.get(field)
        ]
        
        if missing_fields:
            state.errors.append({
                'node': 'administrative_law',
                'error': f'Câmpuri obligatorii lipsă: {", ".join(missing_fields)}',
                'timestamp': datetime.now().isoformat()
            })
            return 'error', state
        
        # Check urgency and public interest
        is_urgent = analysis.get('urgency', False)
        public_interest = analysis.get('public_interest', False)
        
        complexity_score = 1
        if is_urgent and public_interest:
            complexity_score = 3
        elif is_urgent or public_interest:
            complexity_score = 2
        
        # Update state
        state.input_analysis.update({
            'domain_specific': {
                'type': 'administrative',
                'complexity_score': complexity_score,
                'urgent_procedure': is_urgent,
                'public_interest': public_interest,
                'required_documents': [
                    'cerere_suspendare' if is_urgent else 'cerere_anulare',
                    'contestatie_administrativa'
                ]
            }
        })
        
        state.completed_nodes.append('administrative_law')
        return ('expert_consultation' if complexity_score >= 2 else 'document_planning'), state
        
    except Exception as e:
        logger.error(f"Error in administrative_law_node: {str(e)}")
        state.errors.append({
            'node': 'administrative_law',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state

async def labor_law_node(state: AgentState) -> Tuple[str, AgentState]:
    """
    Specialized node for labor law cases.
    """
    try:
        # Validate required fields
        analysis = state.input_analysis.get('legal_analysis', {})
        missing_fields = [
            field for field in DOMAIN_VALIDATORS['labor']['required_fields']
            if not analysis.get(field)
        ]
        
        if missing_fields:
            state.errors.append({
                'node': 'labor_law',
                'error': f'Câmpuri obligatorii lipsă: {", ".join(missing_fields)}',
                'timestamp': datetime.now().isoformat()
            })
            return 'error', state
        
        # Check special conditions
        is_collective = analysis.get('collective_aspects', False)
        is_discrimination = analysis.get('discrimination', False)
        is_safety = analysis.get('workplace_safety', False)
        
        complexity_score = 1
        if sum([is_collective, is_discrimination, is_safety]) >= 2:
            complexity_score = 3
        elif any([is_collective, is_discrimination, is_safety]):
            complexity_score = 2
        
        # Update state
        state.input_analysis.update({
            'domain_specific': {
                'type': 'labor',
                'complexity_score': complexity_score,
                'special_conditions': {
                    'collective': is_collective,
                    'discrimination': is_discrimination,
                    'safety': is_safety
                },
                'required_documents': DOMAIN_VALIDATORS['labor']['document_types']
            }
        })
        
        state.completed_nodes.append('labor_law')
        return ('expert_consultation' if complexity_score >= 2 else 'document_planning'), state
        
    except Exception as e:
        logger.error(f"Error in labor_law_node: {str(e)}")
        state.errors.append({
            'node': 'labor_law',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })
        return 'error', state 