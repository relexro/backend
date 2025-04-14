#!/bin/bash
# Script to import data into Vertex AI Search (Discovery Engine)
set -e

# Help function
function show_help {
  echo "Usage: $0 [OPTIONS]"
  echo "Import data into Vertex AI Search (Discovery Engine) data store"
  echo ""
  echo "Options:"
  echo "  -p, --project-id PROJECT_ID    Google Cloud project ID (required)"
  echo "  -b, --bucket-name BUCKET       Source GCS bucket name (required)"
  echo "  -j, --jurisprudence-path PATH  Path to jurisprudence data in bucket (default: jurisprudenta)"
  echo "  -l, --legislation-path PATH    Path to legislation data in bucket (default: legislatie)"
  echo "  -d, --datastore-suffix SUFFIX  Suffix for datastore ID (default: main-rag-datastore)"
  echo "  -h, --help                     Show this help message"
  echo ""
  echo "Example:"
  echo "  $0 --project-id=relex-123456 --bucket-name=relex-vertex-data"
}

# Parse arguments
PROJECT_ID=""
BUCKET_NAME=""
JURISPRUDENCE_PATH="jurisprudenta"
LEGISLATION_PATH="legislatie"
DATASTORE_SUFFIX="main-rag-datastore"

while (( "$#" )); do
  case "$1" in
    -p|--project-id)
      PROJECT_ID="$2"
      shift 2
      ;;
    --project-id=*)
      PROJECT_ID="${1#*=}"
      shift
      ;;
    -b|--bucket-name)
      BUCKET_NAME="$2"
      shift 2
      ;;
    --bucket-name=*)
      BUCKET_NAME="${1#*=}"
      shift
      ;;
    -j|--jurisprudence-path)
      JURISPRUDENCE_PATH="$2"
      shift 2
      ;;
    --jurisprudence-path=*)
      JURISPRUDENCE_PATH="${1#*=}"
      shift
      ;;
    -l|--legislation-path)
      LEGISLATION_PATH="$2"
      shift 2
      ;;
    --legislation-path=*)
      LEGISLATION_PATH="${1#*=}"
      shift
      ;;
    -d|--datastore-suffix)
      DATASTORE_SUFFIX="$2"
      shift 2
      ;;
    --datastore-suffix=*)
      DATASTORE_SUFFIX="${1#*=}"
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    *)
      echo "Error: Unsupported option $1" >&2
      show_help
      exit 1
      ;;
  esac
done

# Validate required arguments
if [[ -z "$PROJECT_ID" ]]; then
  echo "Error: Project ID is required" >&2
  show_help
  exit 1
fi

if [[ -z "$BUCKET_NAME" ]]; then
  echo "Error: Bucket name is required" >&2
  show_help
  exit 1
fi

# Extract project name from project ID (e.g., "relex" from "relex-123456")
PROJECT_NAME=$(echo $PROJECT_ID | cut -d'-' -f1)
DATASTORE_ID="${PROJECT_NAME}-${DATASTORE_SUFFIX}"

echo "=== Vertex AI Search Data Import ==="
echo "Project ID: $PROJECT_ID"
echo "Project Name: $PROJECT_NAME"
echo "Data Store ID: $DATASTORE_ID"
echo "Bucket Name: $BUCKET_NAME"
echo "Jurisprudence Path: $JURISPRUDENCE_PATH"
echo "Legislation Path: $LEGISLATION_PATH"
echo "=================================="

# Check if gcloud components are up to date
echo "Checking Google Cloud SDK components..."
gcloud components update --quiet

# Check if discovery-engine command is available
if ! gcloud help discovery-engine > /dev/null 2>&1; then
  echo "Installing discovery-engine component..."
  gcloud components install alpha beta --quiet
fi

# Import jurisprudence data
echo "Importing jurisprudence data..."
JURISPRUDENCE_OP=$(gcloud discovery-engine documents import \
  --project=${PROJECT_ID} \
  --location=global \
  --collection=default_collection \
  --data-store=${DATASTORE_ID} \
  --gcs-source-uri=gs://${BUCKET_NAME}/${JURISPRUDENCE_PATH}/*.txt \
  --content-config=CONTENT_UNSTRUCTURED_TEXT \
  --quiet 2>&1)

JURISPRUDENCE_STATUS=$?
if [ $JURISPRUDENCE_STATUS -eq 0 ]; then
  echo "Jurisprudence import started successfully."
  echo "Operation: $JURISPRUDENCE_OP"
else
  echo "Error importing jurisprudence data: $JURISPRUDENCE_OP" >&2
fi

# Import legislation data
echo "Importing legislation data..."
LEGISLATION_OP=$(gcloud discovery-engine documents import \
  --project=${PROJECT_ID} \
  --location=global \
  --collection=default_collection \
  --data-store=${DATASTORE_ID} \
  --gcs-source-uri=gs://${BUCKET_NAME}/${LEGISLATION_PATH}/*.txt \
  --content-config=CONTENT_UNSTRUCTURED_TEXT \
  --quiet 2>&1)

LEGISLATION_STATUS=$?
if [ $LEGISLATION_STATUS -eq 0 ]; then
  echo "Legislation import started successfully."
  echo "Operation: $LEGISLATION_OP"
else
  echo "Error importing legislation data: $LEGISLATION_OP" >&2
fi

echo ""
echo "To monitor import operations, run:"
echo "gcloud discovery-engine operations list --project=${PROJECT_ID} --location=global"
echo ""
echo "To view detailed status of an operation, run:"
echo "gcloud discovery-engine operations describe OPERATION_ID --project=${PROJECT_ID} --location=global"

if [ $JURISPRUDENCE_STATUS -eq 0 ] && [ $LEGISLATION_STATUS -eq 0 ]; then
  exit 0
else
  exit 1
fi 