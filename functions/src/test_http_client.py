import requests
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pdf_http_function():
    """Test the PDF generation HTTP function"""
    try:
        logger.info("Testing PDF HTTP function")
        
        # URL of the PDF function (local server)
        url = "http://localhost:8080"
        
        # Send GET request
        logger.info(f"Sending GET request to {url}")
        response = requests.get(url)
        
        # Check status code
        if response.status_code == 200:
            # Check content type
            content_type = response.headers.get('Content-Type')
            if content_type == 'application/pdf':
                logger.info(f"Received PDF response. Content size: {len(response.content)} bytes")
                
                # Save the PDF for inspection
                output_file = f"http_test_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
                with open(output_file, "wb") as f:
                    f.write(response.content)
                    
                logger.info(f"PDF saved to {output_file}")
                return True
            else:
                logger.error(f"Unexpected content type: {content_type}")
                return False
        else:
            logger.error(f"HTTP request failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing HTTP function: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    success = test_pdf_http_function()
    if success:
        logger.info("✅ HTTP PDF function test PASSED")
    else:
        logger.error("❌ HTTP PDF function test FAILED")
    
    exit(0 if success else 1) 