# Cloud Functions Deployment Troubleshooting Report

## Issue: Container Healthcheck Failures

During the deployment of Google Cloud Functions, we encountered persistent "Container Healthcheck Failed" errors. The error message consistently indicated that the functions weren't properly listening on `PORT=8080`, which is required by Google Cloud Functions.

## Root Causes Identified

1. **Improper Port Listening**: The functions-framework in the Python code was not properly listening on the port defined by the `PORT` environment variable.

2. **LangGraph Workflow Issues**: In `agent_nodes.py`, there was an invalid reference to a 'start' node in the LangGraph workflow that was causing the container to fail.

## Attempted Solutions

### 1. Addressing the PORT=8080 Issue

We attempted several approaches to fix the port listening issue:

- **Added listening code to main.py**:
  ```python
  if __name__ == "__main__":
      PORT = int(os.getenv('PORT', 8080))
      functions_framework.start(host="0.0.0.0", port=PORT)
  ```
  
- **Created minimal test function** (`minimal_test.py`) with explicit port listening:
  ```python
  @functions_framework.http
  def minimal_test(request):
      return jsonify({"status": "success", "message": "Function is working correctly"})

  if __name__ == "__main__":
      PORT = int(os.getenv('PORT', 8080))
      functions_framework.start(port=PORT, host="0.0.0.0")
  ```

- **Created a Flask app** (`app.py`) with a simpler approach:
  ```python
  @app.route('/', methods=['GET'])
  def health_check():
      return jsonify({"status": "healthy", "message": "Service is running"})
      
  if __name__ == "__main__":
      PORT = int(os.getenv('PORT', 8080))
      app.run(host='0.0.0.0', port=PORT, debug=False)
  ```

### 2. Addressing the LangGraph 'start' Node Issue

Fixed `agent_nodes.py` by:
- Removing `workflow.add_edge("start", "determine_tier")`
- Adding `workflow.set_entry_point("determine_tier")`

### 3. Created Helper Scripts for Debugging and Iterative Deployment

Developed several bash scripts to help with the manual testing and deployment process:

- **deploy-test.sh**: For testing single functions with custom parameters
- **deploy-individual.sh**: Interactive script for deploying functions one by one
- **test-function.sh**: Tool to test deployed functions with HTTP requests
- **delete-function.sh**: Tool to clean up test deployments

## Why Solutions Didn't Work

Despite these attempts, the container healthcheck failures persisted due to several possible factors:

1. **Functions Framework Behavior**: The Google Cloud Functions runtime might be executing the code in a way that doesn't trigger the `if __name__ == "__main__"` block, meaning our port listening code was never reached.

2. **Root Cause in Base Container**: The issue may be in how the base container for Python functions is configured, which would require a different approach than modifying the code.

3. **Terraform Service Account Issues**: There was evidence of service account issues in the logs: `Service account projects/-/serviceAccounts/relex-backend@relexro.iam.gserviceaccount.com was not found.`

## Next Steps Recommendation

1. **Use Cloud Run Directly**: Skip the Cloud Functions abstraction and deploy the applications directly to Cloud Run for more control over the container configuration.

2. **Verify Service Account**: Ensure the service account exists and has proper permissions.

3. **Use a More Explicit Framework**: Consider switching to a framework like FastAPI or Flask with an explicit WSGI server like Gunicorn that provides clearer control over port binding.

4. **Consult Google Cloud Support**: If problems persist, reach out to Google Cloud support with the specific error logs for more targeted assistance. 