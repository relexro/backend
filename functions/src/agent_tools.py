"""
Agent Tools - External service integrations for the Lawyer AI Agent
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import aiohttp
import json
import markdown2
from weasyprint import HTML, CSS
from google.cloud import bigquery, firestore, storage
from google.cloud.exceptions import NotFound
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize clients
db = firestore.Client()
storage_client = storage.Client()

# PDF styling
PDF_STYLES = CSS(string='''
    @page {
        size: A4;
        margin: 2.5cm 2cm;
        @top-right {
            content: "Pagina " counter(page) " din " counter(pages);
            font-size: 9pt;
            font-family: "Arial", sans-serif;
        }
    }
    body {
        font-family: "Arial", sans-serif;
        font-size: 11pt;
        line-height: 1.5;
    }
    h1 {
        font-size: 18pt;
        color: #2c3e50;
        margin-bottom: 1.5cm;
        text-align: center;
    }
    h2 {
        font-size: 14pt;
        color: #34495e;
        margin-top: 1cm;
        margin-bottom: 0.5cm;
    }
    p {
        margin-bottom: 0.5cm;
        text-align: justify;
    }
    .header {
        text-align: center;
        margin-bottom: 2cm;
    }
    .footer {
        margin-top: 2cm;
        text-align: center;
        font-size: 9pt;
        color: #7f8c8d;
    }
    .signature {
        margin-top: 2cm;
        page-break-inside: avoid;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 1cm 0;
    }
    th, td {
        border: 1px solid #bdc3c7;
        padding: 0.3cm;
        text-align: left;
    }
    th {
        background-color: #f5f6fa;
    }
''')

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
    party_name: str
) -> Dict[str, Any]:
    """
    Get party ID from name in case context.
    """
    try:
        # Query parties subcollection
        parties_ref = db.collection('cases').document(case_id).collection('parties')
        query = parties_ref.where('name', '==', party_name).limit(1)
        
        parties = query.stream()
        party_list = list(parties)
        
        if not party_list:
            return {
                'status': 'error',
                'message': f"Party {party_name} not found"
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

async def query_bigquery(
    query: str,
    dataset: str
) -> Dict[str, Any]:
    """
    Execute a query against BigQuery legal database.
    """
    try:
        client = bigquery.Client()
        
        # Prepare query with dataset
        full_query = f"""
        SELECT *
        FROM `{dataset}`
        WHERE {query}
        LIMIT 100
        """
        
        # Run query
        query_job = client.query(full_query)
        results = query_job.result()
        
        # Convert results to list of dicts
        rows = []
        for row in results:
            rows.append(dict(row.items()))
        
        return {
            'status': 'success',
            'results': rows,
            'total_rows': len(rows)
        }
        
    except Exception as e:
        logger.error(f"Error querying BigQuery: {str(e)}")
        raise DatabaseError(f"Failed to query legal database: {str(e)}")

async def generate_draft_pdf(
    case_id: str,
    content: str,
    draft_name: str,
    version: int
) -> Dict[str, Any]:
    """
    Generate a PDF draft and store it in Cloud Storage.
    
    Args:
        case_id: The ID of the case
        content: Markdown content to convert to PDF
        draft_name: Name of the draft document
        version: Version number of the draft
        
    Returns:
        Dictionary containing the status and URL of the generated PDF
    """
    try:
        # Get case details for metadata
        case_ref = db.collection('cases').document(case_id)
        case_doc = case_ref.get()
        
        if not case_doc.exists:
            raise PDFGenerationError(f"Case {case_id} not found")
            
        case_data = case_doc.to_dict()
        
        # Convert markdown to HTML with metadata
        html_content = _prepare_html_content(
            content,
            case_data,
            draft_name,
            version
        )
        
        # Create temporary file for PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
            try:
                # Generate PDF
                HTML(string=html_content).write_pdf(
                    temp_pdf.name,
                    stylesheets=[PDF_STYLES]
                )
                
                # Upload to Cloud Storage
                bucket_name = 'relex-legal-drafts'  # Replace with your bucket name
                storage_path = f"cases/{case_id}/drafts/{draft_name}_v{version}.pdf"
                
                bucket = storage_client.bucket(bucket_name)
                blob = bucket.blob(storage_path)
                
                # Upload with metadata
                blob.upload_from_filename(
                    temp_pdf.name,
                    content_type='application/pdf',
                    metadata={
                        'case_id': case_id,
                        'draft_name': draft_name,
                        'version': str(version),
                        'generated_at': datetime.now().isoformat(),
                        'generated_by': 'relex-agent'
                    }
                )
                
                # Generate signed URL (valid for 7 days)
                url = blob.generate_signed_url(
                    version='v4',
                    expiration=datetime.now() + timedelta(days=7),
                    method='GET'
                )
                
                # Update case document with draft information
                draft_info = {
                    'draft_id': f"{case_id}_{draft_name}_v{version}",
                    'name': draft_name,
                    'version': version,
                    'storage_path': storage_path,
                    'url': url,
                    'generated_at': datetime.now().isoformat(),
                    'status': 'generated'
                }
                
                case_ref.update({
                    'drafts': firestore.ArrayUnion([draft_info])
                })
                
                return {
                    'status': 'success',
                    'url': url,
                    'storage_path': storage_path,
                    'version': version,
                    'generated_at': datetime.now().isoformat(),
                    'metadata': draft_info
                }
                
            finally:
                # Clean up temporary file
                os.unlink(temp_pdf.name)
                
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}")
        raise PDFGenerationError(f"Failed to generate PDF: {str(e)}")

def _prepare_html_content(
    content: str,
    case_data: Dict[str, Any],
    draft_name: str,
    version: int
) -> str:
    """
    Prepare HTML content for PDF generation with proper styling and metadata.
    """
    try:
        # Convert markdown to HTML
        html_body = markdown2.markdown(
            content,
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
        
        # Create HTML template with metadata
        html_template = f"""
        <!DOCTYPE html>
        <html lang="ro">
        <head>
            <meta charset="UTF-8">
            <title>{draft_name} - v{version}</title>
            <meta name="generator" content="Relex Legal AI">
            <meta name="case-number" content="{case_number}">
            <meta name="court" content="{court_name}">
            <meta name="document-type" content="{case_type}">
        </head>
        <body>
            <div class="header">
                <h1>{draft_name}</h1>
                <p>Dosar nr. {case_number}</p>
                <p>{court_name}</p>
                <p>Versiunea {version}</p>
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
    error_message: str,
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a support ticket in the ticketing system.
    """
    try:
        # Create ticket document
        ticket_ref = db.collection('support_tickets').document()
        
        ticket_data = {
            'case_id': case_id,
            'error_message': error_message,
            'context': context,
            'status': 'open',
            'priority': 'high',
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
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

async def consult_grok(
    case_id: str,
    context: Dict[str, Any],
    query: str
) -> Dict[str, Any]:
    """
    Consult Grok AI for guidance on legal matters.
    """
    try:
        # Prepare request to Grok API
        grok_request = {
            'case_id': case_id,
            'context': context,
            'query': query,
            'language': 'ro'  # Romanian language
        }
        
        # TODO: Replace with actual Grok API endpoint
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'https://api.grok.ai/v1/legal/guidance',
                json=grok_request,
                headers={'Authorization': 'Bearer YOUR_API_KEY'}
            ) as response:
                if response.status != 200:
                    raise GrokError(f"Grok API returned status {response.status}")
                
                result = await response.json()
                
                return {
                    'status': 'success',
                    'guidance': result.get('guidance', {}),
                    'confidence_score': result.get('confidence', 0.0),
                    'references': result.get('references', [])
                }
                
    except Exception as e:
        logger.error(f"Error consulting Grok: {str(e)}")
        raise GrokError(f"Failed to get Grok guidance: {str(e)}")

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

async def search_legal_database(query: str) -> List[Dict[str, Any]]:
    """
    Search the legal database for relevant cases and legislation.
    """
    try:
        # Execute BigQuery search
        search_results = await query_bigquery(
            query,
            'legal_database.romanian_cases'
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
    """
    try:
        # Query legislation collection
        legislation_ref = db.collection('legislation')
        query = legislation_ref.where('domain', '==', domain).limit(50)
        
        legislation_docs = query.stream()
        
        return [
            {
                'id': doc.id,
                **doc.to_dict()
            }
            for doc in legislation_docs
        ]
        
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