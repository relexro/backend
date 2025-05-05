"""
Test script to verify xhtml2pdf works for generating PDFs from HTML.
This script should run successfully in a Cloud Functions environment.
"""
import os
import sys
import io
from xhtml2pdf import pisa
import markdown2

def convert_markdown_to_pdf(markdown_content, output_path="test_output.pdf"):
    """Convert markdown to PDF using xhtml2pdf."""
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

        # Create HTML template with metadata and CSS styles
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
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Test PDF Document</h1>
            </div>

            <div class="content">
                {html_body}
            </div>

            <div class="footer">
                <p>Generated with xhtml2pdf</p>
            </div>
        </body>
        </html>
        """

        # Convert HTML to PDF
        with open(output_path, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(
                html_template,
                dest=pdf_file,
                encoding='UTF-8'
            )

        # Return success/error
        return not pisa_status.err, pisa_status.err
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return False, str(e)

def test_in_memory_pdf():
    """Test creating a PDF in memory without writing to disk."""
    try:
        html = "<html><body><h1>In-Memory PDF Test</h1><p>This is a test.</p></body></html>"
        
        # Create PDF in memory
        output = io.BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=output)
        
        # Check if creation was successful
        success = not pisa_status.err
        
        # Get PDF content if successful
        if success:
            pdf_content = output.getvalue()
            output.close()
            print(f"In-memory PDF created successfully! Size: {len(pdf_content)} bytes")
        else:
            print(f"Error creating in-memory PDF: {pisa_status.err}")
        
        return success
    
    except Exception as e:
        print(f"Exception in in-memory test: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing xhtml2pdf for Cloud Functions...")
    
    # Test markdown to PDF conversion
    test_markdown = """
# Sample Markdown Document

This is a sample markdown document with some **bold** and *italic* text.

## Section 1

- Item 1
- Item 2
- Item 3

## Section 2

Here's a table:

| Name | Value |
|------|-------|
| A    | 1     |
| B    | 2     |
| C    | 3     |

"""
    
    # Run tests
    print("\nTest 1: Converting markdown to PDF...")
    success, error = convert_markdown_to_pdf(test_markdown)
    if success:
        print(f"Success! PDF saved to test_output.pdf")
    else:
        print(f"Failed to convert markdown to PDF: {error}")
    
    print("\nTest 2: Creating PDF in memory...")
    if test_in_memory_pdf():
        print("In-memory PDF test passed!")
    else:
        print("In-memory PDF test failed!")
    
    print("\nAll tests completed.") 