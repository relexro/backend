# Relex Cloud Functions

This directory contains Cloud Functions deployed to Google Cloud Functions for running the Relex backend services.

## PDF Generation

The system uses `xhtml2pdf` for PDF generation, which is a pure Python library with no system dependencies. This solution was chosen after encountering deployment issues with WeasyPrint, which requires system-level dependencies that are not available in Cloud Functions.

### Benefits of xhtml2pdf:

- Pure Python implementation with no system dependencies
- Works reliably in Cloud Functions environment
- Handles Romanian characters properly
- Generates well-formatted PDF documents from markdown content
- Smaller deployment size

### Testing

Several test scripts are available to validate PDF generation functionality:

- `src/test_pdf_generation.py`: Basic PDF generation test
- `src/test_minimal_pdf.py`: Minimal PDF generation without Firestore dependencies
- `src/test_summary.py`: Runs all tests and generates a summary report

To run all tests:

```bash
cd src
python test_summary.py
```

### Deployment

A unified deployment script (`deploy.sh`) is provided to deploy all Cloud Functions including the PDF generator. The script:

1. Deploys functions with appropriate memory, concurrency, and timeout settings
2. Configures higher resources for the PDF generation function
3. Sets up proper service account and region settings

To deploy the functions:

```bash
chmod +x deploy.sh
./deploy.sh
```

## Development

### Local Testing

You can test the PDF generation functionality locally:

1. Run `python src/test_minimal_pdf.py` to generate a test PDF
2. Check `src/test_output.pdf` for the generated output

### Important Notes

- PDF generation is resource-intensive, so the PDF generator function has higher memory allocation and lower concurrency settings
- PDF files are stored in Cloud Storage with signed URLs for access
- The PDF generation logic is implemented in `src/agent_tools.py` in the `generate_draft_pdf` function

## Function Endpoints

- PDF Generator: https://europe-west1-relexro.cloudfunctions.net/pdf-generator
- Agent Handler: https://europe-west1-relexro.cloudfunctions.net/agent-handler
- And other endpoints as deployed by the deploy.sh script 