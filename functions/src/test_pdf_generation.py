import asyncio
import logging
from google.cloud import firestore
import os
import tempfile
from xhtml2pdf import pisa
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_basic_pdf_generation():
    """Test basic PDF generation with xhtml2pdf"""
    logger.info("Testing basic PDF generation with xhtml2pdf")
    
    # Create a simple HTML document
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Test PDF</title>
        <style>
            body { font-family: Arial, sans-serif; }
            h1 { color: #003366; }
            .content { margin: 20px; }
        </style>
    </head>
    <body>
        <h1>Test PDF Document</h1>
        <div class="content">
            <p>This is a test PDF document generated with xhtml2pdf.</p>
            <p>If you can see this content in a PDF, the generation works correctly.</p>
            <p>This confirms the pure Python PDF generation is working in the Cloud Functions environment.</p>
        </div>
    </body>
    </html>
    """
    
    # Create a temporary file for the PDF output
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_pdf:
        try:
            # Generate PDF
            logger.info(f"Creating PDF file at: {temp_pdf.name}")
            pdf_file = open(temp_pdf.name, "wb")
            
            # Create PDF
            pisa_status = pisa.CreatePDF(
                html_content,
                dest=pdf_file,
                encoding='UTF-8'
            )
            pdf_file.close()
            
            # Check if PDF conversion was successful
            if pisa_status.err:
                logger.error(f"PDF conversion failed: {pisa_status.err}")
                return False
            
            # Check file size
            file_size = os.path.getsize(temp_pdf.name)
            logger.info(f"PDF generated successfully. File size: {file_size} bytes")
            
            # Read the PDF content to verify
            with open(temp_pdf.name, "rb") as f:
                pdf_content = f.read()
                
            # Verify PDF content (just checking if it starts with %PDF which is the PDF header)
            if pdf_content.startswith(b'%PDF'):
                logger.info("PDF content verification successful")
                return True
            else:
                logger.error("PDF content doesn't have a valid PDF header")
                return False
                
        except Exception as e:
            logger.error(f"Error during PDF generation: {str(e)}", exc_info=True)
            return False
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_pdf.name)
                logger.info(f"Temporary file deleted: {temp_pdf.name}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file: {str(e)}")

def run_tests():
    """Run all tests"""
    logger.info("Starting PDF generation tests")
    
    # Test basic PDF generation
    basic_test_result = test_basic_pdf_generation()
    
    # Print results
    if basic_test_result:
        logger.info("✅ Basic PDF generation test PASSED")
    else:
        logger.error("❌ Basic PDF generation test FAILED")
    
    logger.info("PDF generation tests completed")
    return basic_test_result

if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1) 