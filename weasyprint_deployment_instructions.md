# Instructions for handling weasyprint deployment

## Deployment Issues with WeasyPrint

WeasyPrint requires system dependencies that can cause issues when deploying to cloud environments like Google Cloud Functions. Here's how to solve the deployment issues:

## Option 1: Include system dependencies in your deployment

For Google Cloud Functions, you can use a custom runtime with the required dependencies:

1. Add a `.dockerignore` file to exclude unnecessary files
2. Create a `Dockerfile` in your project root:

```dockerfile
FROM python:3.9-slim

# Install WeasyPrint dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    libffi-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY . .

CMD [ "python", "-m", "functions-framework", "--target=http_endpoint" ]
```

3. Update your deployment command to use the Dockerfile:

```bash
gcloud functions deploy pdf-generator \
  --gen2 \
  --runtime=python39 \
  --source=. \
  --entry-point=http_endpoint \
  --trigger-http \
  --allow-unauthenticated
```

## Option 2: Use Cloud Run instead of Cloud Functions

Cloud Run offers more flexibility with custom containers, making it easier to include the required system dependencies:

1. Create the Dockerfile as described above
2. Build and deploy to Cloud Run:

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/pdf-generator
gcloud run deploy pdf-generator --image gcr.io/YOUR_PROJECT_ID/pdf-generator --platform managed
```

## Option 3: Use a separate service for PDF generation

If you're facing persistent issues with deploying WeasyPrint, you can:

1. Create a small dedicated service specifically for PDF generation
2. Deploy it to Cloud Run or a VM where you have more control over the environment
3. Have your Cloud Functions call this service when PDF generation is needed

## Troubleshooting

If you encounter specific errors during deployment:

1. For missing libraries errors: Check that all system dependencies are included in your Dockerfile
2. For memory issues: Increase the memory allocation for your cloud function
3. For timeout issues: Increase the timeout duration for your function 

# PDF Generation in Cloud Functions

## Previous Issue with WeasyPrint

WeasyPrint requires system dependencies that cause issues when deploying to Cloud Functions. We've implemented a pure Python solution that works natively in Cloud Functions.

## Our Solution: xhtml2pdf

We've replaced WeasyPrint with xhtml2pdf, a pure Python HTML-to-PDF converter:

### Benefits:
- No system dependencies required
- Works natively in Cloud Functions
- No external API services needed
- Easy to deploy and maintain

### Implementation Details:

1. We're using xhtml2pdf, which is a pure Python library with no system dependencies
2. HTML content (converted from markdown) is passed directly to xhtml2pdf
3. The PDF is generated entirely within the Cloud Function
4. The PDF is then stored in Google Cloud Storage as before

### Configuration:

No special configuration required - just deploy as you would any normal Cloud Function:

```bash
gcloud functions deploy pdf-generator \
  --runtime=python39 \
  --source=./functions \
  --entry-point=http_endpoint \
  --trigger-http
```

### Code Example:

```python
from xhtml2pdf import pisa
import io

# Create an in-memory PDF
pdf_output = io.BytesIO()
pisa.CreatePDF(
    html_content,      # HTML content string
    dest=pdf_output,   # Output file handle
    encoding='UTF-8'   # Ensure proper encoding
)

# Get the PDF content
pdf_content = pdf_output.getvalue()
pdf_output.close()
```

## Testing Your PDF Generation

To test PDF generation locally:

```bash
cd functions/src
pip install -r requirements.txt
python -c "from xhtml2pdf import pisa; import io; pdf=io.BytesIO(); pisa.CreatePDF('<html><body><h1>Test PDF</h1></body></html>', dest=pdf); open('test.pdf', 'wb').write(pdf.getvalue())"
```

## Deployment Instructions

To deploy your Cloud Function with xhtml2pdf:

```bash
cd functions
gcloud functions deploy pdf-generator \
  --gen2 \
  --runtime=python39 \
  --source=. \
  --entry-point=http_endpoint \
  --trigger-http
```

No external services, no system dependencies, no Docker required! 