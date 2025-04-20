"""
Response Templates - Structured templates for legal advice and document generation
"""
from typing import Dict, Any, List
from datetime import datetime
import json

# Base templates for different response types
GENERAL_ADVICE_TEMPLATE = """
{salutation}

{initial_analysis}

{legal_basis}

{case_law_references}

{recommendations}

{next_steps}

Cu stimă,
Asistentul Juridic Relex
"""

DOCUMENT_DRAFT_TEMPLATE = """
# {document_title}

## Preambul
Data: {current_date}
Referință: {case_reference}

## Părți
{parties_section}

## Context
{context_section}

## Obiectul Documentului
{document_purpose}

## Conținut Principal
{main_content}

## Dispoziții Finale
{final_provisions}

## Semnături
{signatures_section}
"""

COURT_SUBMISSION_TEMPLATE = """
Către
{court_name}
{court_section}

DOMNULE/DOAMNA PREȘEDINTE,

Subsemnatul/Subsemnata {plaintiff_details},
în contradictoriu cu {defendant_details},

FORMULEZ PREZENTA
{submission_type}

{submission_content}

În drept, îmi întemeiez cererea pe dispozițiile:
{legal_basis}

În dovedirea cererii, înțeleg să mă folosesc de următoarele:
{evidence_list}

Pentru aceste motive, vă rog să dispuneți:
{requests}

Data: {current_date}
Semnătura,
{signature}
"""

LEGAL_ANALYSIS_TEMPLATE = """
# Analiză Juridică
Caz: {case_reference}
Data: {current_date}

## Sumar Executiv
{executive_summary}

## Cadrul Legal Aplicabil
{legal_framework}

## Analiza Situației
{situation_analysis}

## Jurisprudență Relevantă
{relevant_cases}

## Concluzii și Recomandări
{conclusions}

## Riscuri și Considerații
{risks_and_considerations}
"""

CONTRACT_TEMPLATE = """
CONTRACT {contract_type}
Nr. {contract_number} din {current_date}

I. PĂRȚILE CONTRACTANTE
{parties_details}

II. OBIECTUL CONTRACTULUI
{contract_object}

III. DURATA CONTRACTULUI
{contract_duration}

IV. PREȚUL ȘI MODALITATEA DE PLATĂ
{payment_terms}

V. DREPTURI ȘI OBLIGAȚII
{rights_and_obligations}

VI. ÎNCETAREA CONTRACTULUI
{termination_conditions}

VII. LITIGII
{dispute_resolution}

VIII. CLAUZE FINALE
{final_clauses}

Prezentul contract a fost încheiat astăzi, {current_date}, în două exemplare originale, câte unul pentru fiecare parte.

SEMNĂTURI
{signatures}
"""

def format_response(
    template_type: str,
    context: Dict[str, Any],
    research_results: List[Dict[str, Any]],
    guidance: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Format a response using the appropriate template.
    """
    try:
        # Common context
        base_context = {
            "current_date": datetime.now().strftime("%d.%m.%Y"),
            "case_reference": context.get("case_id", "N/A")
        }
        
        if template_type == "general_advice":
            return _format_general_advice(base_context, research_results, guidance)
        elif template_type == "document_draft":
            return _format_document_draft(base_context, context, research_results)
        elif template_type == "court_submission":
            return _format_court_submission(base_context, context, guidance)
        elif template_type == "legal_analysis":
            return _format_legal_analysis(base_context, research_results, guidance)
        elif template_type == "contract":
            return _format_contract(base_context, context)
        else:
            raise ValueError(f"Unknown template type: {template_type}")
            
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _format_general_advice(
    base_context: Dict[str, Any],
    research_results: List[Dict[str, Any]],
    guidance: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Format a general legal advice response."""
    try:
        # Extract relevant case law references
        case_law = "\n".join([
            f"• {result.get('case_number')}: {result.get('summary')}"
            for result in research_results[:3]  # Top 3 most relevant
        ])
        
        # Get latest guidance
        latest_guidance = guidance[-1] if guidance else {}
        
        response = GENERAL_ADVICE_TEMPLATE.format(
            salutation="Stimată/Stimate client,",
            initial_analysis=latest_guidance.get("initial_analysis", ""),
            legal_basis=latest_guidance.get("legal_basis", ""),
            case_law_references=f"Jurisprudență relevantă:\n{case_law}",
            recommendations=latest_guidance.get("recommendations", ""),
            next_steps=latest_guidance.get("next_steps", "")
        )
        
        return {
            "status": "success",
            "response": response.strip(),
            "should_generate_draft": False
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _format_document_draft(
    base_context: Dict[str, Any],
    context: Dict[str, Any],
    research_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Format a legal document draft."""
    try:
        # Get parties information
        parties = context.get("parties", [])
        parties_section = "\n".join([
            f"• {party.get('name')}\n  {party.get('details')}"
            for party in parties
        ])
        
        response = DOCUMENT_DRAFT_TEMPLATE.format(
            document_title=context.get("document_title", "Document Juridic"),
            current_date=base_context["current_date"],
            case_reference=base_context["case_reference"],
            parties_section=parties_section,
            context_section=context.get("situation_summary", ""),
            document_purpose=context.get("purpose", ""),
            main_content=context.get("main_content", ""),
            final_provisions=context.get("final_provisions", ""),
            signatures_section=context.get("signatures", "")
        )
        
        return {
            "status": "success",
            "response": response.strip(),
            "should_generate_draft": True,
            "draft_name": context.get("document_title", "document").lower().replace(" ", "_"),
            "draft_content": response
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _format_court_submission(
    base_context: Dict[str, Any],
    context: Dict[str, Any],
    guidance: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Format a court submission document."""
    try:
        # Get latest guidance
        latest_guidance = guidance[-1] if guidance else {}
        
        response = COURT_SUBMISSION_TEMPLATE.format(
            court_name=context.get("court_name", ""),
            court_section=context.get("court_section", ""),
            plaintiff_details=context.get("plaintiff_details", ""),
            defendant_details=context.get("defendant_details", ""),
            submission_type=context.get("submission_type", "CERERE"),
            submission_content=latest_guidance.get("submission_content", ""),
            legal_basis=latest_guidance.get("legal_basis", ""),
            evidence_list=latest_guidance.get("evidence_list", ""),
            requests=latest_guidance.get("requests", ""),
            current_date=base_context["current_date"],
            signature="[Semnătură]"
        )
        
        return {
            "status": "success",
            "response": response.strip(),
            "should_generate_draft": True,
            "draft_name": f"cerere_{context.get('submission_type', '').lower()}",
            "draft_content": response
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _format_legal_analysis(
    base_context: Dict[str, Any],
    research_results: List[Dict[str, Any]],
    guidance: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Format a detailed legal analysis."""
    try:
        # Get latest guidance
        latest_guidance = guidance[-1] if guidance else {}
        
        # Format relevant cases
        relevant_cases = "\n".join([
            f"• {result.get('case_number')} - {result.get('summary')}"
            for result in research_results[:5]  # Top 5 most relevant
        ])
        
        response = LEGAL_ANALYSIS_TEMPLATE.format(
            case_reference=base_context["case_reference"],
            current_date=base_context["current_date"],
            executive_summary=latest_guidance.get("executive_summary", ""),
            legal_framework=latest_guidance.get("legal_framework", ""),
            situation_analysis=latest_guidance.get("situation_analysis", ""),
            relevant_cases=relevant_cases,
            conclusions=latest_guidance.get("conclusions", ""),
            risks_and_considerations=latest_guidance.get("risks", "")
        )
        
        return {
            "status": "success",
            "response": response.strip(),
            "should_generate_draft": True,
            "draft_name": "analiza_juridica",
            "draft_content": response
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def _format_contract(
    base_context: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """Format a contract document."""
    try:
        response = CONTRACT_TEMPLATE.format(
            contract_type=context.get("contract_type", ""),
            contract_number=context.get("contract_number", ""),
            current_date=base_context["current_date"],
            parties_details=context.get("parties_details", ""),
            contract_object=context.get("contract_object", ""),
            contract_duration=context.get("contract_duration", ""),
            payment_terms=context.get("payment_terms", ""),
            rights_and_obligations=context.get("rights_and_obligations", ""),
            termination_conditions=context.get("termination_conditions", ""),
            dispute_resolution=context.get("dispute_resolution", ""),
            final_clauses=context.get("final_clauses", ""),
            signatures=context.get("signatures", "")
        )
        
        return {
            "status": "success",
            "response": response.strip(),
            "should_generate_draft": True,
            "draft_name": f"contract_{context.get('contract_type', '').lower()}",
            "draft_content": response
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        } 