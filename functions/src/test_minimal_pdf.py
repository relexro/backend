import io
import logging
import os
import tempfile
from xhtml2pdf import pisa
import markdown2
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_simple_pdf(markdown_content):
    """Generate a simple PDF from markdown content"""
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
        
        # Create HTML template with CSS styles
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>Test PDF Document</title>
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
                h1 {{
                    color: #003366;
                    text-align: center;
                    margin-bottom: 1cm;
                }}
                h2 {{
                    color: #003366;
                    margin-top: 0.8cm;
                    margin-bottom: 0.3cm;
                }}
                h3 {{
                    color: #003366;
                    margin-top: 0.5cm;
                    margin-bottom: 0.2cm;
                }}
                p {{
                    margin-bottom: 0.3cm;
                    text-align: justify;
                }}
                ul, ol {{
                    margin-bottom: 0.5cm;
                }}
                footer {{
                    text-align: center;
                    font-size: 9pt;
                    margin-top: 1cm;
                    border-top: 1px solid #cccccc;
                    padding-top: 0.2cm;
                }}
            </style>
        </head>
        <body>
            <div class="content">
                {html_body}
            </div>
            <footer>
                Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}
            </footer>
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
                    html_template,
                    dest=pdf_file,
                    encoding='UTF-8'
                )
                pdf_file.close()
                
                # Check if PDF conversion was successful
                if pisa_status.err:
                    logger.error(f"PDF conversion failed: {pisa_status.err}")
                    return False, None
                
                # Check file size
                file_size = os.path.getsize(temp_pdf.name)
                logger.info(f"PDF generated successfully. File size: {file_size} bytes")
                
                # Read the PDF content
                with open(temp_pdf.name, "rb") as f:
                    pdf_content = f.read()
                
                # Return success and content
                return True, pdf_content
                
            except Exception as e:
                logger.error(f"Error during PDF generation: {str(e)}", exc_info=True)
                return False, None
            finally:
                # Clean up the temporary file
                os.unlink(temp_pdf.name)
                logger.info(f"Temporary file deleted: {temp_pdf.name}")
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return False, None

def test_minimal_pdf():
    """Run a minimal PDF generation test"""
    
    # Test markdown content
    markdown_content = """
# Test Document Title

## Introduction

This is a test document generated with xhtml2pdf to verify that PDF generation works correctly.

## Features

* Pure Python PDF generation without system dependencies
* Works in Cloud Functions environment
* Handles Romanian characters: șțăîâ

## Sample Table

| Name | Value | Description |
|------|-------|-------------|
| Item 1 | 100 | This is item 1 |
| Item 2 | 200 | This is item 2 |
| Item 3 | 300 | This is item 3 |

## Conclusion

If you can see this document correctly formatted as a PDF, the test was successful.
"""
    
    # Generate PDF
    success, pdf_content = generate_simple_pdf(markdown_content)
    
    # Verify result
    if success:
        logger.info("✅ Minimal PDF generation test PASSED")
        
        # Save to a file for manual inspection
        with open("test_output.pdf", "wb") as f:
            f.write(pdf_content)
        logger.info(f"PDF saved to test_output.pdf for inspection")
        
        return True
    else:
        logger.error("❌ Minimal PDF generation test FAILED")
        return False

if __name__ == "__main__":
    logger.info("Starting minimal PDF generation test")
    result = test_minimal_pdf()
    exit(0 if result else 1) 