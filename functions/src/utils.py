"""
Utility functions for the Relex agent and backend services.
"""
from typing import Dict, Any
from datetime import datetime

def prepare_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepares and sanitizes context for LLM processing, ensuring correct data types.

    Args:
        context: The input context dictionary.

    Returns:
        A sanitized context dictionary.
    """
    prepared = {
        "timestamp": datetime.now().isoformat(),
        "language": "ro" # Default language
    }

    # Safely get and convert claim_value to float if it exists
    if 'claim_value' in context and context['claim_value'] is not None:
        try:
            prepared['claim_value'] = float(context['claim_value'])
        except (ValueError, TypeError):
            # Keep original value if conversion fails, could be handled later
            prepared['claim_value'] = context['claim_value']

    # Ensure legal_basis and parties are lists of strings
    if 'legal_basis' in context and context['legal_basis'] is not None:
        prepared['legal_basis'] = [str(item) for item in context['legal_basis']]
    
    if 'parties' in context and context['parties'] is not None:
        prepared['parties'] = [str(item) for item in context['parties']]

    # Copy other relevant fields
    for key in ['case_type', 'precedents', 'urgency', 'enable_fallback', 'track_performance']:
        if key in context:
            prepared[key] = context[key]
    
    return prepared 