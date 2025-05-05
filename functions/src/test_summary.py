import logging
import os
import json
import subprocess
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test(test_file):
    """Run a test script and return success status"""
    logger.info(f"Running test: {test_file}")
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            check=False,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            logger.info(f"✅ {test_file} - PASSED")
            return True
        else:
            logger.error(f"❌ {test_file} - FAILED")
            logger.error(f"Error output: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error running {test_file}: {str(e)}")
        return False

def run_all_tests():
    """Run all PDF generation tests"""
    logger.info("Starting PDF functionality test suite")
    
    # Test files to run
    test_files = [
        "test_pdf_generation.py",  # Basic PDF generation test
        "test_minimal_pdf.py",     # Minimal PDF generation test
    ]
    
    results = {}
    all_passed = True
    
    # Run each test
    for test_file in test_files:
        if os.path.exists(test_file):
            success = run_test(test_file)
            results[test_file] = "PASSED" if success else "FAILED"
            if not success:
                all_passed = False
        else:
            logger.warning(f"Test file not found: {test_file}")
            results[test_file] = "NOT FOUND"
            all_passed = False
    
    # Print summary
    logger.info("\n" + "-" * 50)
    logger.info("PDF TEST SUMMARY")
    logger.info("-" * 50)
    
    for test_file, status in results.items():
        status_icon = "✅" if status == "PASSED" else "❌"
        logger.info(f"{status_icon} {test_file}: {status}")
    
    logger.info("-" * 50)
    logger.info(f"OVERALL STATUS: {'✅ PASSED' if all_passed else '❌ FAILED'}")
    logger.info("-" * 50)
    
    # Create PDF test verification summary file
    summary = {
        "test_date": __import__("datetime").datetime.now().isoformat(),
        "tests": results,
        "overall_status": "PASSED" if all_passed else "FAILED",
        "environment": {
            "python_version": sys.version,
            "system": sys.platform
        }
    }
    
    with open("pdf_test_results.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Test summary saved to pdf_test_results.json")
    
    return all_passed

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1) 