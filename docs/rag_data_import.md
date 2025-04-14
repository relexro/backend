# Vertex AI Search Data Import Process

This document describes the process for importing data into the Vertex AI Search (Discovery Engine) data store created by the Terraform RAG module.

## Automated Import using Script

The easiest way to import data is using the provided script:

```bash
# Basic usage
./scripts/import_rag_data.sh --project-id=your-project-id --bucket-name=your-bucket-name

# Example with all options
./scripts/import_rag_data.sh \
  --project-id=relex-123456 \
  --bucket-name=relex-vertex-data \
  --jurisprudence-path=jurisprudenta \
  --legislation-path=legislatie \
  --datastore-suffix=main-rag-datastore
```

### Script Options

The script accepts the following options:

| Option | Description | Default |
|--------|-------------|---------|
| `-p, --project-id` | Google Cloud project ID (required) | - |
| `-b, --bucket-name` | Source GCS bucket name (required) | - |
| `-j, --jurisprudence-path` | Path to jurisprudence data in bucket | `jurisprudenta` |
| `-l, --legislation-path` | Path to legislation data in bucket | `legislatie` |
| `-d, --datastore-suffix` | Suffix for datastore ID | `main-rag-datastore` |
| `-h, --help` | Show help message | - |

The script will:
1. Check and update your gcloud components if needed
2. Import jurisprudence data from the specified bucket path
3. Import legislation data from the specified bucket path
4. Provide commands to monitor the import operations

## Manual Import Process

If you prefer to import data manually, follow the steps below.

## Prerequisites

Before you begin, ensure you have:

1. Successfully deployed the RAG Terraform module which creates:
   - A Discovery Engine data store
   - A Discovery Engine search engine

2. Required Google Cloud SDK tools installed and updated:
   ```bash
   gcloud components update
   gcloud components install alpha beta
   ```

3. Source data ready for import:
   - Text files (TXT) containing legal documents
   - Optional metadata in a JSONL file

## Step 1: Set Environment Variables

For convenience, set environment variables for your project and data store information:

```bash
# Set your Google Cloud project ID
export PROJECT_ID="your-project-id"

# Extract the project name part from the project ID (e.g., "relex" from "relex-123456")
export PROJECT_NAME=$(echo $PROJECT_ID | cut -d'-' -f1)

# Set the data store suffix as defined in Terraform
export DATASTORE_SUFFIX="main-rag-datastore"

# Combine to form the complete data store ID
export DATASTORE_ID="${PROJECT_NAME}-${DATASTORE_SUFFIX}"
```

## Step 2: Prepare Your Data

There are two primary methods for importing data:

### Option A: Import from Cloud Storage

1. Create a Cloud Storage bucket (if not already created):
   ```bash
   gsutil mb -l europe-west1 gs://${PROJECT_ID}-rag-data
   ```

2. Upload your documents to the bucket:
   ```bash
   gsutil cp -r /path/to/your/documents/* gs://${PROJECT_ID}-rag-data/
   ```

### Option B: Import from Local Files (with cloud storage intermediate step)

1. Create a temporary Cloud Storage bucket:
   ```bash
   gsutil mb -l europe-west1 gs://${PROJECT_ID}-temp-rag-data
   ```

2. Upload your documents to the bucket:
   ```bash
   gsutil cp -r /path/to/your/documents/* gs://${PROJECT_ID}-temp-rag-data/
   ```

## Step 3: Import Data into Discovery Engine

### For Unstructured Documents (TXT files)

```bash
gcloud discovery-engine documents import \
  --project=${PROJECT_ID} \
  --location=global \
  --collection=default_collection \
  --data-store=${DATASTORE_ID} \
  --gcs-source-uri=gs://${PROJECT_ID}-rag-data/* \
  --content-config=CONTENT_UNSTRUCTURED_TEXT
```

### For Structured Documents (with metadata in JSONL format)

```bash
gcloud discovery-engine documents import \
  --project=${PROJECT_ID} \
  --location=global \
  --collection=default_collection \
  --data-store=${DATASTORE_ID} \
  --gcs-source-uri=gs://${PROJECT_ID}-rag-data/metadata.jsonl \
  --content-config=NO_CONTENT
```

## Step 4: Monitor Import Status

Check the status of your import operation:

```bash
gcloud discovery-engine operations list \
  --project=${PROJECT_ID} \
  --location=global \
  --filter="metadata.dataStore=${DATASTORE_ID}"
```

Get details about a specific import operation:

```bash
gcloud discovery-engine operations describe OPERATION_ID \
  --project=${PROJECT_ID} \
  --location=global
```

## Step 5: Verify Data Import

List the documents in your data store:

```bash
gcloud discovery-engine documents list \
  --project=${PROJECT_ID} \
  --location=global \
  --collection=default_collection \
  --data-store=${DATASTORE_ID} \
  --limit=10
```

## Troubleshooting

### Common Issues

1. **Command not found**: If `gcloud discovery-engine` commands are not found, make sure you have installed the latest Google Cloud SDK components:
   ```bash
   gcloud components update
   gcloud components install alpha beta
   ```

2. **Permission denied**: Ensure your user account or service account has the necessary IAM permissions:
   ```bash
   gcloud projects add-iam-policy-binding ${PROJECT_ID} \
     --member="user:your-email@example.com" \
     --role="roles/discoveryengine.admin"
   ```

3. **Import errors**: Check the operation status for detailed error messages.

### Recommended Practices

1. **Start with a small set of documents** for testing before importing your entire collection.
2. **Use content chunking** for large documents to improve search relevance.
3. **Add metadata** to your documents to enhance search capabilities.
4. **Test search queries** after import to verify data is accessible and properly indexed.

## Advanced Configuration

### Document Schema

For structured data imports with a JSONL file, each line should contain a JSON object with the following structure:

```json
{
  "id": "unique-document-id",
  "jsonData": {
    "title": "Document Title",
    "content": "Full document content...",
    "metadata": {
      "author": "Author Name",
      "publishedDate": "2023-04-15",
      "category": "Legal",
      "tags": ["legislation", "civil-code"]
    }
  }
}
```

### Custom Import Options

For more advanced import configurations, refer to the [official Google Cloud documentation](https://cloud.google.com/generative-ai-app-builder/docs/import-data-search).

## References

- [Google Cloud Discovery Engine Documentation](https://cloud.google.com/discovery-engine/docs)
- [Data Import Guide for Vertex AI Search](https://cloud.google.com/generative-ai-app-builder/docs/import-data-search) 