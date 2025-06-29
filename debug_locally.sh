#!/bin/bash

# This script creates an isolated environment to replicate the Cloud Function startup process locally.
# It will reveal any fatal errors that occur during module import.

echo "--- Setting up isolated Python environment in ./.venv ---"
python3 -m venv .venv

echo "--- Activating environment ---"
source .venv/bin/activate

echo "--- Installing exact dependencies from requirements.txt ---"
pip install -r functions/src/requirements.txt

echo "--- Attempting to start the 'create_case' function locally ---"
echo "--- If the application has a startup error, it will crash and display here ---"

# We use functions-framework to run the function locally, simulating the cloud environment.
# We point it to the main.py file and specify the target function to run.
functions-framework --source=functions/src/main.py --target=relex_backend_create_case --debug

echo "--- Deactivating environment ---"
deactivate 