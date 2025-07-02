"""
Agent Tools - External service integrations for the Lawyer AI Agent
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import aiohttp
import json
import markdown2
# Pure Python PDF libraries without system dependencies
from xhtml2pdf import pisa
import io
from google.cloud import firestore, storage
from google.cloud.exceptions import NotFound
import tempfile
import os
import base64
from langchain_xai import ChatXAI
from langchain_core.messages import SystemMessage, HumanMessage
import os
from exa_py import Exa
from langchain.tools import tool
from common.clients import get_secret
from firebase_admin import firestore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
db = firestore.Client()
storage_client = storage.Client()

# --- Tool-specific Errors ---
class ExaToolError(Exception):
    """Custom exception for Exa API tool errors."""
    pass

# --- Exa Client Initialization ---
try:
    exa_api_key = get_secret("EXA_API_KEY")
    exa = Exa(api_key=exa_api_key)
except Exception as e:
    # If the secret is not available at import time, handle it gracefully.
    # The tools will fail at runtime if the client is not initialized.
    exa = None
    print(f"WARNING: Exa client could not be initialized at import time: {e}")

# --- New Exa Tools ---

@tool
def find_legislation(query: str, country_domain_filter: str = None) -> str:
    """
    Searches for official legislation, statutes, or laws using Exa.
    `country_domain_filter` should be a 'site:' filter for a government domain.
    """
    if not exa:
        raise ExaToolError("Exa client is not initialized. Check API key secret.")
    print(f"---EXA_TOOL: Searching for legislation with query: '{query}'---")
    try:
        search_results = exa.search(
            f"{query} {country_domain_filter if country_domain_filter else ''}",
            use_autoprompt=True,
            type="neural",
            num_results=5
        )
        return str(search_results)
    except Exception as e:
        raise ExaToolError(f"Exa find_legislation failed: {e}")

@tool
def find_case_law(query: str, jurisdiction: str = None) -> str:
    """
    Searches for case law, court decisions, or legal precedents using Exa.
    """
    if not exa:
        raise ExaToolError("Exa client is not initialized. Check API key secret.")
    print(f"---EXA_TOOL: Searching for case law with query: '{query}'---")
    try:
        full_query = f"case law {query}"
        if jurisdiction:
            full_query += f" in {jurisdiction}"
        
        search_results = exa.search(
            full_query,
            use_autoprompt=True,
            type="neural",
            num_results=5
        )
        return str(search_results)
    except Exception as e:
        raise ExaToolError(f"Exa find_case_law failed: {e}")

@tool
def get_verbatim_content(result_ids: list[str]) -> str:
    """
    Retrieves the full, clean, verbatim text of web pages from a list of Exa result IDs.
    """
    if not exa:
        raise ExaToolError("Exa client is not initialized. Check API key secret.")
    print(f"---EXA_TOOL: Getting verbatim content for IDs: {result_ids}---")
    try:
        contents = exa.get_contents(result_ids, text=True, highlights=False)
        return str(contents)
    except Exception as e:
        raise ExaToolError(f"Exa get_verbatim_content failed: {e}")

@tool
def find_contact_info(institution_name: str) -> str:
    """
    Searches for contact information for a specific legal institution using Exa.
    """
    if not exa:
        raise ExaToolError("Exa client is not initialized. Check API key secret.")
    print(f"---EXA_TOOL: Searching for contact info for: '{institution_name}'---")
    try:
        search_results = exa.search(
            f"contact information for {institution_name} official website",
            use_autoprompt=True,
            num_results=3
        )
        return str(search_results)
    except Exception as e:
        raise ExaToolError(f"Exa find_contact_info failed: {e}")

# List of the new tools to be used by the agent orchestrator
legal_tools = [find_legislation, find_case_law, get_verbatim_content, find_contact_info]

class QuotaError(Exception):
    """Custom exception for quota-related errors."""
    pass

class PaymentError(Exception):
    """Custom exception for payment-related errors."""
    pass

class DatabaseError(Exception):
    """Custom exception for database operation errors."""
    pass

class GrokError(Exception):
    """Custom exception for Grok API errors."""
    pass

class PDFGenerationError(Exception):
    """Custom exception for PDF generation errors."""
    pass

async def check_quota(
    user_id: str,
    organization_id: Optional[str] = None,
    case_tier: int = 1
) -> Dict[str, Any]:
    """
    Check user's quota and payment status.
    """
    try:
        # Get user document
        user_ref = db.collection('users').document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            raise QuotaError(f"User {user_id} not found")

        user_data = user_doc.to_dict()

        # Get quota limits based on subscription
        subscription = user_data.get('subscription', {})
        quota_limit = subscription.get('quota_limit', 0)
        quota_used = subscription.get('quota_used', 0)

        # Check organization quota if applicable
        if organization_id:
            org_ref = db.collection('organizations').document(organization_id)
            org_doc = org_ref.get()
            if org_doc.exists:
                org_data = org_doc.to_dict()
                org_quota_limit = org_data.get('quota_limit', 0)
                org_quota_used = org_data.get('quota_used', 0)

                # Use the higher quota limit
                quota_limit = max(quota_limit, org_quota_limit)
                quota_used = min(quota_used, org_quota_used)

        # Calculate remaining quota
        remaining_quota = quota_limit - quota_used
        requires_payment = case_tier > subscription.get('tier', 0)

        return {
            'status': 'success',
            'available_requests': remaining_quota,
            'requires_payment': requires_payment,
            'subscription_tier': subscription.get('tier', 0),
            'quota_limit': quota_limit,
            'quota_used': quota_used
        }

    except Exception as e:
        logger.error(f"Error checking quota: {str(e)}")
        raise QuotaError(f"Failed to check quota: {str(e)}")

async def get_case_details(case_id: str) -> Dict[str, Any]:
    """
    Retrieve case details from Firestore.
    """
    try:
        case_ref = db.collection('cases').document(case_id)
        case_doc = case_ref.get()

        if not case_doc.exists:
            raise DatabaseError(f"Case {case_id} not found")

        return {
            'status': 'success',
            'case_details': case_doc.to_dict()
        }

    except Exception as e:
        logger.error(f"Error getting case details: {str(e)}")
        raise DatabaseError(f"Failed to get case details: {str(e)}")

async def update_case_details(
    case_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update case details in Firestore.
    """
    try:
        case_ref = db.collection('cases').document(case_id)

        # Add timestamp to updates
        updates['last_updated'] = firestore.SERVER_TIMESTAMP

        # Update the document
        case_ref.update(updates)

        return {
            'status': 'success',
            'updated_at': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error updating case details: {str(e)}")
        raise DatabaseError(f"Failed to update case details: {str(e)}")

async def get_party_id_by_name(
    case_id: str,
    mentioned_name: str
) -> Dict[str, Any]:
    """
    Looks up the internal partyId for a party mentioned by name within the current case context.

    Args:
        case_id: The ID of the current case context
        mentioned_name: The first name or alias used by the user to refer to the party

    Returns:
        Dictionary containing the party ID and basic metadata
    """
    try:
        # Query parties subcollection
        parties_ref = db.collection('cases').document(case_id).collection('parties')
        query = parties_ref.where('name', '==', mentioned_name).limit(1)

        parties = query.stream()
        party_list = list(parties)

        if not party_list:
            return {
                'status': 'error',
                'message': f"Party {mentioned_name} not found"
            }

        party_doc = party_list[0]
        return {
            'status': 'success',
            'party_id': party_doc.id,
            'party_data': party_doc.to_dict()
        }

    except Exception as e:
        logger.error(f"Error getting party ID: {str(e)}")
        raise DatabaseError(f"Failed to get party ID: {str(e)}")

async def generate_draft_pdf(
    case_id: str,
    markdown_content: str,
    draft_name: str,
    revision: int
) -> Dict[str, Any]:
    """
    Generate a PDF document from markdown content and store it in Cloud Storage.
    Uses xhtml2pdf which is a pure Python library with no system dependencies.

    Args:
        case_id: The ID of the case
        markdown_content: The markdown content to convert to PDF
        draft_name: The name of the draft document
        revision: The revision number

    Returns:
        Dictionary containing the URL to the generated PDF and metadata
    """
    logger.info(f"Starting PDF generation for case {case_id}, draft {draft_name}, revision {revision}")
    
    try:
        # Get case reference
        case_ref = db.collection('cases').document(case_id)
        case_doc = case_ref.get()

        if not case_doc.exists:
            logger.error(f"Case {case_id} not found")
            raise PDFGenerationError(f"Case {case_id} not found")

        case_data = case_doc.to_dict()
        
        # Log important steps
        logger.info(f"Converting markdown to HTML for case {case_id}")

        # Convert markdown to HTML with metadata
        html_content = _prepare_html_content(
            markdown_content,
            case_data,
            draft_name,
            revision
        )

        # Log PDF generation
        logger.info(f"Starting xhtml2pdf conversion for case {case_id}")

        # Create temporary file for PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            try:
                # Generate PDF using xhtml2pdf (pure Python, no system dependencies)
                logger.info(f"Creating PDF file at: {temp_pdf.name}")
                pdf_file = open(temp_pdf.name, "wb")
                
                # Log the HTML content length
                logger.info(f"HTML content length: {len(html_content)} characters")
                
                # Create PDF with detailed error logging
                pisa_status = pisa.CreatePDF(
                    html_content,           # HTML content to convert
                    dest=pdf_file,          # Output file handle
                    encoding='UTF-8'        # Ensure proper encoding
                )
                pdf_file.close()

                # Check if PDF conversion was successful
                if pisa_status.err:
                    error_msg = f"PDF conversion failed: {pisa_status.err}"
                    logger.error(error_msg)
                    raise PDFGenerationError(error_msg)

                # Check file size
                file_size = os.path.getsize(temp_pdf.name)
                logger.info(f"PDF generated successfully. File size: {file_size} bytes")
                
                # Upload to Cloud Storage
                bucket_name = 'relex-legal-drafts'  # Replace with your bucket name
                storage_path = f"cases/{case_id}/drafts/{draft_name}_v{revision}.pdf"
                
                logger.info(f"Uploading PDF to Cloud Storage: {storage_path}")

                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(storage_path)

                # Upload with metadata
                blob.upload_from_filename(
                    temp_pdf.name,
                    content_type='application/pdf',
                    metadata={
                        'case_id': case_id,
                        'draft_name': draft_name,
                        'version': str(revision),
                        'generated_at': datetime.now().isoformat(),
                        'generated_by': 'relex-agent'
                    }
                )
                
                logger.info(f"PDF uploaded successfully to {storage_path}")

                # Generate signed URL (valid for 7 days)
                url = blob.generate_signed_url(
                    version='v4',
                    expiration=datetime.now() + timedelta(days=7),
                    method='GET'
                )
                
                logger.info(f"Generated signed URL with 7-day expiration")

                # Update case document with draft information
                draft_info = {
                    'draft_id': f"{case_id}_{draft_name}_v{revision}",
                    'name': draft_name,
                    'version': revision,
                    'storage_path': storage_path,
                    'url': url,
                    'generated_at': datetime.now().isoformat(),
                    'status': 'generated'
                }

                logger.info(f"Updating case document with draft information")
                case_ref.update({
                    'drafts': firestore.ArrayUnion([draft_info])
                })

                logger.info(f"PDF generation completed successfully for case {case_id}")
                return {
                    'status': 'success',
                    'url': url,
                    'storage_path': storage_path,
                    'version': revision,
                    'generated_at': datetime.now().isoformat(),
                    'metadata': draft_info
                }

            except Exception as e:
                error_msg = f"Error during PDF generation process: {str(e)}"
                logger.error(error_msg, exc_info=True)
                raise PDFGenerationError(error_msg)
            finally:
                # Clean up temporary file
                logger.info(f"Cleaning up temporary file: {temp_pdf.name}")
                os.unlink(temp_pdf.name)

    except Exception as e:
        error_msg = f"Error generating PDF: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise PDFGenerationError(error_msg)

def _prepare_html_content(
    markdown_content: str,
    case_data: Dict[str, Any],
    draft_name: str,
    revision: int
) -> str:
    """
    Prepare HTML content for PDF generation with proper styling and metadata.
    """
    try:
        # Convert markdown to HTML
        html_body = markdown2.markdown(
            markdown_content,
            extras=[
                'tables',
                'fenced-code-blocks',
                'header-ids',
                'toc'
            ]
        )

        # Get case metadata
        case_number = case_data.get('case_number', 'N/A')
        court_name = case_data.get('court_name', 'N/A')
        case_type = case_data.get('case_type', 'N/A')

        # Create HTML template with metadata and CSS styles
        html_template = f"""
        <!DOCTYPE html>
        <html lang="ro">
        <head>
            <meta charset="UTF-8">
            <title>{draft_name} - v{revision}</title>
            <meta name="generator" content="Relex Legal AI">
            <meta name="case-number" content="{case_number}">
            <meta name="court" content="{court_name}">
            <meta name="document-type" content="{case_type}">
            <style>
                @page {{
                    size: A4;
                    margin: 2cm;
                }}
                body {{
                    font-family: Arial, Helvetica, sans-serif;
                    line-height: 1.5;
                    font-size: 12pt;
                }}
                .header {{
                    margin-bottom: 2cm;
                }}
                .header h1 {{
                    font-size: 18pt;
                    margin-bottom: 0.5cm;
                }}
                .content {{
                    margin-bottom: 2cm;
                }}
                .footer {{
                    font-size: 10pt;
                    margin-top: 1cm;
                    border-top: 1px solid #ccc;
                    padding-top: 0.5cm;
                }}
                .signature {{
                    margin-top: 2cm;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{draft_name}</h1>
                <p>Dosar nr. {case_number}</p>
                <p>{court_name}</p>
                <p>Versiunea {revision}</p>
            </div>

            <div class="content">
                {html_body}
            </div>

            <div class="footer">
                <p>Document generat la {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p>Relex Legal AI - Asistent Juridic</p>
            </div>

            <div class="signature">
                <p>Semnătură: _____________________</p>
                <p>Data: _____________________</p>
            </div>
        </body>
        </html>
        """

        return html_template

    except Exception as e:
        logger.error(f"Error preparing HTML content: {str(e)}")
        raise PDFGenerationError(f"Failed to prepare HTML content: {str(e)}")

async def create_support_ticket(
    case_id: str,
    issue_description: str,
    agent_state_snapshot: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Creates a support ticket when the agent encounters an unrecoverable error.
    Also pauses the case.

    Args:
        case_id: The ID of the case experiencing the issue
        issue_description: Detailed description of the problem encountered by the agent
        agent_state_snapshot: Optional snapshot of relevant agent state at time of failure

    Returns:
        Dictionary containing the ticket ID and creation timestamp
    """
    try:
        # Create ticket document
        ticket_ref = db.collection('support_tickets').document()

        ticket_data = {
            'case_id': case_id,
            'issue_description': issue_description,
            'agent_state_snapshot': agent_state_snapshot or {},
            'status': 'open',
            'priority': 'high',
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }

        # Update case status to paused_support
        case_ref = db.collection('cases').document(case_id)
        case_ref.update({
            'status': 'paused_support',
            'support_ticket_id': ticket_ref.id,
            'paused_at': firestore.SERVER_TIMESTAMP
        })

        ticket_ref.set(ticket_data)

        return {
            'status': 'success',
            'ticket_id': ticket_ref.id,
            'created_at': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error creating support ticket: {str(e)}")
        # Don't raise here - this is a fallback mechanism
        return {
            'status': 'error',
            'error': str(e)
        }

async def consult_grok(case_id: str, context: dict, specific_question: str) -> dict:
    """
    Consults the Grok model via the official LangChain XAI integration.

    Args:
        case_id: The ID of the case for logging and context.
        context: A dictionary containing the context for the query.
        specific_question: The specific question to ask the model.

    Returns:
        A dictionary containing the model's response.
    """
    logger.info(f"Consulting xAI's Grok for case_id: {case_id}")
    try:
        # Use the correct GROK_API_KEY environment variable as defined in the project's terraform variables.
        api_key = os.environ.get("GROK_API_KEY")
        if not api_key:
            logger.error("GROK_API_KEY environment variable not set.")
            raise ValueError("GROK_API_KEY is not configured.")

        # Instantiate the ChatXAI client, passing the API key explicitly.
        llm = ChatXAI(model="grok-1", api_key=api_key)

        # Format the prompt using the provided context and question
        prompt_content = f"""
        Context: {json.dumps(context, indent=2, ensure_ascii=False)}

        Question: {specific_question}
        """

        messages = [
            SystemMessage(content="You are an expert legal analyst. Provide precise and strategic guidance based on the context."),
            HumanMessage(content=prompt_content)
        ]

        # Invoke the model
        response = await llm.ainvoke(messages)
        
        # Return the response content in a structured dictionary.
        return {
            "recommendations": response.content
        }

    except Exception as e:
        logger.error(f"Error consulting Grok for case {case_id}: {str(e)}", exc_info=True)
        # Return a structured error to be handled by the agent.
        return {
            "error": "Failed to consult Grok expert.",
            "details": str(e)
        }

# Additional utility functions

async def verify_payment(case_id: str) -> Dict[str, Any]:
    """
    Verify payment status for a case.
    """
    try:
        case_ref = db.collection('cases').document(case_id)
        case_doc = case_ref.get()

        if not case_doc.exists:
            raise PaymentError(f"Case {case_id} not found")

        case_data = case_doc.to_dict()
        payments = case_data.get('payments', [])

        # Check for valid payment
        valid_payment = any(
            payment.get('status') == 'completed'
            for payment in payments
        )

        return {
            'status': 'success',
            'paid': valid_payment,
            'payment_details': payments[-1] if payments else None
        }

    except Exception as e:
        logger.error(f"Error verifying payment: {str(e)}")
        raise PaymentError(f"Failed to verify payment: {str(e)}")

async def search_legal_database(query: str, table_name: str = 'legislatie') -> List[Dict[str, Any]]:
    """
    Search the legal database for relevant cases and legislation.

    Args:
        query: The search query to execute
        table_name: The target table name ('legislatie' or 'jurisprudenta')

    Returns:
        List of matching documents
    """
    try:
        # Construct a proper SQL query
        sql_query = f"SELECT * FROM `relexro.romanian_legal_data.{table_name}` WHERE {query}"

        # Execute BigQuery search
        search_results = await query_bigquery(
            query_string=sql_query,
            table_name=table_name
        )

        if search_results['status'] != 'success':
            raise DatabaseError("Failed to search legal database")

        return search_results['results']

    except Exception as e:
        logger.error(f"Error searching legal database: {str(e)}")
        raise DatabaseError(f"Failed to search legal database: {str(e)}")

async def get_relevant_legislation(domain: str) -> List[Dict[str, Any]]:
    """
    Get relevant legislation for a legal domain.

    Args:
        domain: The legal domain to search for (e.g., 'civil', 'penal')

    Returns:
        List of relevant legislation documents
    """
    try:
        # Construct a query to find legislation in the specified domain
        sql_query = f"SELECT * FROM `relexro.romanian_legal_data.legislatie` WHERE LOWER(domain) LIKE '%{domain.lower()}%' LIMIT 50"

        # Execute BigQuery search
        search_results = await query_bigquery(
            query_string=sql_query,
            table_name='legislatie'
        )

        if search_results['status'] != 'success':
            raise DatabaseError("Failed to get relevant legislation")

        return search_results['results']

    except Exception as e:
        logger.error(f"Error getting legislation: {str(e)}")
        raise DatabaseError(f"Failed to get legislation: {str(e)}")

async def update_quota_usage(
    user_id: str,
    organization_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update quota usage for user and organization.
    """
    try:
        # Update user quota
        user_ref = db.collection('users').document(user_id)
        user_ref.update({
            'subscription.quota_used': firestore.Increment(1)
        })

        # Update organization quota if applicable
        if organization_id:
            org_ref = db.collection('organizations').document(organization_id)
            org_ref.update({
                'quota_used': firestore.Increment(1)
            })

        return {
            'status': 'success',
            'updated_at': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error updating quota usage: {str(e)}")
        raise QuotaError(f"Failed to update quota usage: {str(e)}")