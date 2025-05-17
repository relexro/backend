# Monitoring and Logging

This document provides guidance on monitoring and logging for the Relex Backend system.

## Cloud Logging

### API Gateway Logs

API Gateway logs are available in Cloud Logging but with a specific configuration:

1. **Resource Type**: API Gateway logs use `resource.type=api` (not `resource.type=api_gateway` as might be expected)
2. **Log Name Pattern**: The logs have a `logName` containing `apigateway` (e.g., `projects/relexro/logs/relex-api-dev-1zpirx0ouzrnu.apigateway.relexro.cloud.goog%2Fendpoints_log`)

#### Accessing API Gateway Logs

There are two recommended ways to access API Gateway logs:

1. **Using the Dedicated Log Views**:
   - Two dedicated log views have been created in the `_Default` log bucket:
     - `api-gateway-logs`: Uses a specific filter with `LOG_ID("relex-api-dev-1zpirx0ouzrnu.apigateway.relexro.cloud.goog/endpoints_log")`
     - `api-gateway-logs-broader`: Uses a broader filter with `resource.type="api"` that will continue to capture API Gateway logs even if the specific LOG_ID changes
   - Access these views in the Google Cloud Console under Logging > Log Explorer > Views

   > **Note**: The `api-gateway-logs` view uses the specific filter `resource.type="api" AND LOG_ID("relex-api-dev-1zpirx0ouzrnu.apigateway.relexro.cloud.goog/endpoints_log")`. This specific `LOG_ID` (especially the `relex-api-dev-1zpirx0ouzrnu` part) may change if the underlying API configuration (`relex-api-dev`) is updated or redeployed. If this happens, the log view's filter will need to be manually updated to the new `LOG_ID` to continue functioning correctly.

   > **Important**: The `api-gateway-logs-broader` view, which filters on `resource.type="api"`, serves as a more stable fallback. It will capture all `resource.type="api"` logs, including API Gateway logs, even if the specific `LOG_ID` changes, though it will be less targeted.

2. **Using a Custom Query**:
   - In the Log Explorer, use the following query:
     ```
     resource.type=api AND logName:apigateway
     ```

#### Log Content

API Gateway logs include valuable information such as:

- HTTP request details (method, URL, status code, latency)
- Client IP addresses
- Error information
- API method being called
- Service configuration ID

### Cloud Function Logs

Cloud Function logs are available under `resource.type=cloud_function` and can be queried using:

```
resource.type=cloud_function
```

To filter for a specific function, use:

```
resource.type=cloud_function AND resource.labels.function_name="relex-backend-[FUNCTION_NAME]"
```

### Firestore Logs

Firestore logs are available under `resource.type=datastore_database` and can be queried using:

```
resource.type=datastore_database
```

## Monitoring

### Health Checks

All API endpoints support health checks via the `X-Google-Health-Check` header. To check the health of any endpoint, send a GET request with this header:

```
GET /v1/any/endpoint
X-Google-Health-Check: true
```

### Cloud Monitoring

Cloud Monitoring provides metrics for various resources:

1. **API Gateway Metrics**:
   - Request count
   - Latency
   - Error rate

2. **Cloud Function Metrics**:
   - Execution count
   - Execution time
   - Memory usage
   - Instance count

3. **Firestore Metrics**:
   - Document read/write operations
   - Query count
   - Storage size

### Creating Custom Dashboards

To create a custom dashboard for API Gateway monitoring:

1. Navigate to Google Cloud Console > Monitoring > Dashboards
2. Click "Create Dashboard"
3. Add widgets for:
   - API Gateway request count
   - API Gateway error rate
   - API Gateway latency
   - Top API methods by request count
   - Recent API Gateway logs (using the query: `resource.type=api AND logName:apigateway`)

## Alerting

Consider setting up alerts for:

1. **Error Rate**: Alert when the API Gateway error rate exceeds a threshold
2. **Latency**: Alert when API Gateway latency exceeds a threshold
3. **Function Errors**: Alert when Cloud Functions report errors
4. **Quota Usage**: Alert when approaching API or resource quotas

## Troubleshooting

### Common Issues

1. **API Gateway Logs Not Appearing**:
   - Ensure you're using the correct query: `resource.type=api AND logName:apigateway`
   - Verify that the API Gateway service account has the `roles/logging.logWriter` permission

2. **Cloud Function Logs Not Appearing**:
   - Verify that the function service account has the `roles/logging.logWriter` permission
   - Check if there are any log exclusions that might be filtering out the logs

3. **Missing Metrics**:
   - Ensure that the Monitoring API is enabled for the project
   - Verify that the service accounts have the necessary permissions

### Useful Commands

```bash
# Check API Gateway logs
gcloud logging read "resource.type=api AND logName:apigateway" --project=relexro --limit=10

# Check Cloud Function logs
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name='relex-backend-[FUNCTION_NAME]'" --project=relexro --limit=10

# List log sinks
gcloud logging sinks list --project=relexro

# List log views
gcloud logging views list --project=relexro --location=global --bucket=_Default
```

## Best Practices

1. **Structured Logging**: Use structured logging in Cloud Functions to make logs more searchable and analyzable
2. **Log Levels**: Use appropriate log levels (INFO, WARNING, ERROR) to distinguish between different types of log entries
3. **Correlation IDs**: Include correlation IDs in logs to track requests across multiple services
4. **Sensitive Data**: Avoid logging sensitive data such as authentication tokens or personal information
5. **Regular Review**: Regularly review logs and metrics to identify potential issues before they become critical
