import asyncio
import logging
from agent_tools import generate_draft_pdf, PDFGenerationError
import os
import tempfile
import uuid
from datetime import datetime
from google.cloud import firestore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firestore client
db = firestore.Client()

async def create_test_case():
    """Create a test case in Firestore for PDF generation testing"""
    try:
        # Generate a unique ID for the test case
        case_id = f"test_case_{uuid.uuid4().hex[:8]}"
        
        # Create basic case data
        case_data = {
            "case_number": f"Test-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "title": "Test Case for PDF Generation",
            "description": "This case was created for testing PDF generation functionality",
            "court_name": "Test Court",
            "case_type": "Test",
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "drafts": []
        }
        
        # Create case document in Firestore
        logger.info(f"Creating test case with ID: {case_id}")
        db.collection('cases').document(case_id).set(case_data)
        
        return case_id
    except Exception as e:
        logger.error(f"Error creating test case: {str(e)}")
        return None

async def cleanup_test_case(case_id):
    """Clean up the test case from Firestore"""
    try:
        logger.info(f"Deleting test case with ID: {case_id}")
        db.collection('cases').document(case_id).delete()
        return True
    except Exception as e:
        logger.error(f"Error deleting test case: {str(e)}")
        return False

async def test_generate_draft_pdf():
    """Test the generate_draft_pdf function from agent_tools.py"""
    
    # Create a test case
    case_id = await create_test_case()
    if not case_id:
        logger.error("Failed to create test case, aborting test")
        return False
    
    try:
        # Generate test markdown content
        markdown_content = """
# Test Legal Document

## Introduction

This is a test legal document generated through the PDF generation tool.

## Main Content

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.

### Subsection

* Item 1
* Item 2
* Item 3

## Conclusion

In conclusion, this test verifies that the PDF generation functionality works correctly.

**Signed on:** {date}
"""
        
        # Set parameters for PDF generation
        draft_name = "Test_Draft"
        revision = 1
        
        logger.info(f"Calling generate_draft_pdf for case: {case_id}")
        
        # Call the generate_draft_pdf function
        result = await generate_draft_pdf(
            case_id=case_id,
            markdown_content=markdown_content,
            draft_name=draft_name,
            revision=revision
        )
        
        # Verify the result
        if result and result.get('status') == 'success' and result.get('url'):
            logger.info(f"PDF generation successful. URL: {result.get('url')}")
            logger.info(f"Storage path: {result.get('storage_path')}")
            return True
        else:
            logger.error(f"PDF generation failed: {result}")
            return False
            
    except PDFGenerationError as e:
        logger.error(f"PDF Generation Error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return False
    finally:
        # Clean up test case
        await cleanup_test_case(case_id)

async def run_tests():
    """Run all tests"""
    logger.info("Starting agent PDF generation tests")
    
    # Test generate_draft_pdf function
    pdf_generation_result = await test_generate_draft_pdf()
    
    # Print results
    if pdf_generation_result:
        logger.info("✅ Agent PDF generation test PASSED")
    else:
        logger.error("❌ Agent PDF generation test FAILED")
    
    logger.info("Agent PDF generation tests completed")
    return pdf_generation_result

if __name__ == "__main__":
    # Run the tests
    loop = asyncio.get_event_loop()
    success = loop.run_until_complete(run_tests())
    exit(0 if success else 1) 