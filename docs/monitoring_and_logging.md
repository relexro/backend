# Monitoring and Logging

This document provides comprehensive guidance on monitoring, logging, and alerting for the Relex Backend system.

## Cloud Logging

### API Gateway Logs

API Gateway logs are available in Cloud Logging with a specific configuration:

1. **Resource Type**: API Gateway logs use `resource.type=api` (not `resource.type=api_gateway` as might be expected)
2. **Log Name Pattern**: The logs have a `logName` containing `apigateway` (e.g., `projects/relexro/logs/relex-api-dev-1zpirx0ouzrnu.apigateway.relexro.cloud.goog%2Fendpoints_log`)

> **Verification**: This logging configuration was verified on 2025-05-17. The logs are being correctly generated and can be successfully retrieved using the recommended query filters.

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
   - For CLI access, use:
     ```bash
     gcloud logging read "resource.type=api AND logName:apigateway" --project=relexro --limit=10
     ```

#### Log Content

API Gateway logs include valuable information such as:

- HTTP request details (method, URL, status code, latency)
- Client IP addresses
- Error information (including HTTP status codes like 403 for authentication issues)
- API method being called (e.g., `Relex_backend_get_user_profile`)
- Service configuration ID
- Timestamp of the request

The logs capture both successful requests and errors, making them valuable for debugging authentication and authorization issues.

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

## Monitoring Framework

### Key Metrics to Monitor

The following metrics are critical for monitoring the health and performance of the Relex Backend system:

#### 1. API Gateway Metrics
- **Request Count**: Total number of API requests
- **Error Rate**: Percentage of requests returning 4xx/5xx status codes
- **Latency**: Response time percentiles (50th, 95th, 99th)
- **Throughput**: Requests per second
- **Status Code Distribution**: Breakdown by HTTP status codes

#### 2. Cloud Function Metrics
- **Execution Count**: Number of function invocations
- **Execution Time**: Function execution duration
- **Memory Usage**: Memory consumption during execution
- **Instance Count**: Number of active function instances
- **Error Rate**: Percentage of failed function executions
- **Cold Start Rate**: Frequency of cold starts

#### 3. Authentication Metrics
- **Authentication Success Rate**: Percentage of successful authentications
- **Token Validation Errors**: Number of invalid/expired tokens
- **Authorization Failures**: Number of 403 Forbidden responses

#### 4. Business Logic Metrics
- **Case Creation Rate**: Number of cases created per time period
- **Agent Interaction Success Rate**: Percentage of successful agent interactions
- **Payment Success Rate**: Percentage of successful payments
- **File Upload Success Rate**: Percentage of successful file uploads

#### 5. Resource Utilization Metrics
- **Firestore Read/Write Operations**: Database operation counts
- **Storage Usage**: Cloud Storage usage and costs
- **Memory and CPU Usage**: Resource consumption by functions

### Alerting Policies

#### 1. High Error Rate Alert
Triggers when the API Gateway error rate exceeds 5% over a 5-minute window.

```bash
gcloud alpha monitoring policies create \
  --policy-from-file=- \
  --project=relexro <<EOF
displayName: "API Gateway High Error Rate"
conditions:
  - displayName: "API Gateway error rate > 5%"
    conditionThreshold:
      filter: 'resource.type="api" AND metric.type="apigateway.googleapis.com/request_count"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.05
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
          crossSeriesReducer: REDUCE_MEAN
          groupByFields:
            - "resource.labels.service"
      trigger:
        count: 1
notificationChannels:
  - projects/relexro/notificationChannels/[CHANNEL_ID]
EOF
```

#### 2. High Latency Alert
Triggers when the 95th percentile latency exceeds 2 seconds.

```bash
gcloud alpha monitoring policies create \
  --policy-from-file=- \
  --project=relexro <<EOF
displayName: "API Gateway High Latency"
conditions:
  - displayName: "API Gateway 95th percentile latency > 2s"
    conditionThreshold:
      filter: 'resource.type="api" AND metric.type="apigateway.googleapis.com/request_latencies"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 2000000
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_PERCENTILE_95
          crossSeriesReducer: REDUCE_MEAN
          groupByFields:
            - "resource.labels.service"
      trigger:
        count: 1
notificationChannels:
  - projects/relexro/notificationChannels/[CHANNEL_ID]
EOF
```

#### 3. Cloud Function Error Alert
Triggers when any Cloud Function has an error rate exceeding 10%.

```bash
gcloud alpha monitoring policies create \
  --policy-from-file=- \
  --project=relexro <<EOF
displayName: "Cloud Function High Error Rate"
conditions:
  - displayName: "Cloud Function error rate > 10%"
    conditionThreshold:
      filter: 'resource.type="cloud_function" AND metric.type="cloudfunctions.googleapis.com/function/execution_count"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.10
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
          crossSeriesReducer: REDUCE_MEAN
          groupByFields:
            - "resource.labels.function_name"
      trigger:
        count: 1
notificationChannels:
  - projects/relexro/notificationChannels/[CHANNEL_ID]
EOF
```

#### 4. Authentication Failure Alert
Triggers when authentication failures exceed 20% over a 10-minute window.

```bash
gcloud alpha monitoring policies create \
  --policy-from-file=- \
  --project=relexro <<EOF
displayName: "High Authentication Failure Rate"
conditions:
  - displayName: "Authentication failure rate > 20%"
    conditionThreshold:
      filter: 'resource.type="api" AND httpRequest.status>=400 AND httpRequest.status<500'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.20
      duration: 600s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
          crossSeriesReducer: REDUCE_MEAN
      trigger:
        count: 1
notificationChannels:
  - projects/relexro/notificationChannels/[CHANNEL_ID]
EOF
```

#### 5. Resource Quota Alert
Triggers when approaching API quotas or resource limits.

```bash
gcloud alpha monitoring policies create \
  --policy-from-file=- \
  --project=relexro <<EOF
displayName: "API Quota Usage Warning"
conditions:
  - displayName: "API quota usage > 80%"
    conditionThreshold:
      filter: 'metric.type="servicemanagement.googleapis.com/quota/allocation/usage"'
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.80
      duration: 300s
      aggregations:
        - alignmentPeriod: 300s
          perSeriesAligner: ALIGN_MEAN
          crossSeriesReducer: REDUCE_MEAN
      trigger:
        count: 1
notificationChannels:
  - projects/relexro/notificationChannels/[CHANNEL_ID]
EOF
```

### Notification Channels Setup

#### 1. Email Notification Channel
```bash
gcloud alpha monitoring channels create \
  --display-name="Relex Backend Alerts" \
  --type="email" \
  --channel-labels="email_address=alerts@relex.ro" \
  --project=relexro
```

#### 2. Slack Notification Channel
```bash
gcloud alpha monitoring channels create \
  --display-name="Relex Backend Slack Alerts" \
  --type="slack" \
  --channel-labels="channel_name=#relex-alerts" \
  --channel-labels="webhook_url=https://hooks.slack.com/services/YOUR/WEBHOOK/URL" \
  --project=relexro
```

#### 3. PagerDuty Notification Channel
```bash
gcloud alpha monitoring channels create \
  --display-name="Relex Backend PagerDuty" \
  --type="pagerduty" \
  --channel-labels="routing_key=YOUR_PAGERDUTY_ROUTING_KEY" \
  --project=relexro
```

### Dashboard Creation

#### 1. API Gateway Dashboard
```bash
gcloud alpha monitoring dashboards create \
  --project=relexro \
  --config-from-file=- <<EOF
displayName: "Relex API Gateway Dashboard"
gridLayout:
  widgets:
    - title: "Request Count"
      xyChart:
        dataSets:
          - timeSeriesQuery:
              timeSeriesFilter:
                filter: 'resource.type="api" AND metric.type="apigateway.googleapis.com/request_count"'
                aggregation:
                  alignmentPeriod: 60s
                  perSeriesAligner: ALIGN_RATE
    - title: "Error Rate"
      xyChart:
        dataSets:
          - timeSeriesQuery:
              timeSeriesFilter:
                filter: 'resource.type="api" AND metric.type="apigateway.googleapis.com/request_count" AND httpRequest.status>=400'
                aggregation:
                  alignmentPeriod: 60s
                  perSeriesAligner: ALIGN_RATE
    - title: "Latency (95th percentile)"
      xyChart:
        dataSets:
          - timeSeriesQuery:
              timeSeriesFilter:
                filter: 'resource.type="api" AND metric.type="apigateway.googleapis.com/request_latencies"'
                aggregation:
                  alignmentPeriod: 60s
                  perSeriesAligner: ALIGN_PERCENTILE_95
EOF
```

#### 2. Cloud Function Dashboard
```bash
gcloud alpha monitoring dashboards create \
  --project=relexro \
  --config-from-file=- <<EOF
displayName: "Relex Cloud Functions Dashboard"
gridLayout:
  widgets:
    - title: "Function Execution Count"
      xyChart:
        dataSets:
          - timeSeriesQuery:
              timeSeriesFilter:
                filter: 'resource.type="cloud_function" AND metric.type="cloudfunctions.googleapis.com/function/execution_count"'
                aggregation:
                  alignmentPeriod: 60s
                  perSeriesAligner: ALIGN_RATE
    - title: "Function Error Rate"
      xyChart:
        dataSets:
          - timeSeriesQuery:
              timeSeriesFilter:
                filter: 'resource.type="cloud_function" AND metric.type="cloudfunctions.googleapis.com/function/execution_count" AND resource.labels.execution_type="error"'
                aggregation:
                  alignmentPeriod: 60s
                  perSeriesAligner: ALIGN_RATE
    - title: "Function Execution Time"
      xyChart:
        dataSets:
          - timeSeriesQuery:
              timeSeriesFilter:
                filter: 'resource.type="cloud_function" AND metric.type="cloudfunctions.googleapis.com/function/execution_times"'
                aggregation:
                  alignmentPeriod: 60s
                  perSeriesAligner: ALIGN_MEAN
EOF
```

### Health Checks

All API endpoints support health checks via the `X-Google-Health-Check` header. To check the health of any endpoint, send a GET request with this header:

```
GET /v1/any/endpoint
X-Google-Health-Check: true
```

### Custom Metrics

#### 1. Business Metrics
Track business-specific metrics using Cloud Monitoring custom metrics:

```python
# Example: Track case creation rate
from google.cloud import monitoring_v3

client = monitoring_v3.MetricServiceClient()
project_name = f"projects/relexro"

series = monitoring_v3.TimeSeries()
series.metric.type = "custom.googleapis.com/cases/created"
series.resource.type = "global"
series.resource.labels["project_id"] = "relexro"

# Add data points
point = series.points.add()
point.value.double_value = 1.0
point.interval.end_time.seconds = int(time.time())

client.create_time_series(request={"name": project_name, "time_series": [series]})
```

#### 2. Agent Performance Metrics
Track AI agent performance and response times:

```python
# Example: Track agent response time
def track_agent_response_time(case_id, response_time_ms):
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/relexro"
    
    series = monitoring_v3.TimeSeries()
    series.metric.type = "custom.googleapis.com/agent/response_time"
    series.metric.labels["case_id"] = case_id
    series.resource.type = "global"
    series.resource.labels["project_id"] = "relexro"
    
    point = series.points.add()
    point.value.double_value = response_time_ms
    point.interval.end_time.seconds = int(time.time())
    
    client.create_time_series(request={"name": project_name, "time_series": [series]})
```

### Log-Based Metrics

#### 1. Error Rate from Logs
Create log-based metrics to track error rates:

```bash
gcloud logging metrics create api-error-rate \
  --description="API error rate based on log entries" \
  --log-filter='resource.type="api" AND severity>=ERROR' \
  --project=relexro
```

#### 2. Authentication Failures from Logs
```bash
gcloud logging metrics create auth-failures \
  --description="Authentication failures from API Gateway logs" \
  --log-filter='resource.type="api" AND httpRequest.status=401' \
  --project=relexro
```

### Troubleshooting

#### Common Issues

1. **API Gateway Logs Not Appearing**:
   - Ensure you're using the correct query: `resource.type=api AND logName:apigateway`
   - Verify that the API Gateway service account has the `roles/logging.logWriter` permission

2. **Cloud Function Logs Not Appearing**:
   - Verify that the function service account has the `roles/logging.logWriter` permission
   - Check if there are any log exclusions that might be filtering out the logs

3. **Missing Metrics**:
   - Ensure that the Monitoring API is enabled for the project
   - Verify that the service accounts have the necessary permissions

4. **Alerts Not Triggering**:
   - Check that notification channels are properly configured
   - Verify that the alerting policies have the correct filters and thresholds
   - Ensure that the Monitoring API is enabled

#### Useful Commands

```bash
# Check API Gateway logs
gcloud logging read "resource.type=api AND logName:apigateway" --project=relexro --limit=10

# Check Cloud Function logs
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name='relex-backend-[FUNCTION_NAME]'" --project=relexro --limit=10

# List log sinks
gcloud logging sinks list --project=relexro

# List log views
gcloud logging views list --project=relexro --location=global --bucket=_Default

# List monitoring policies
gcloud alpha monitoring policies list --project=relexro

# List notification channels
gcloud alpha monitoring channels list --project=relexro

# List dashboards
gcloud alpha monitoring dashboards list --project=relexro

# Check custom metrics
gcloud alpha monitoring metrics list --filter="metric.type=custom.googleapis.com" --project=relexro
```

## Best Practices

1. **Structured Logging**: Use structured logging in Cloud Functions to make logs more searchable and analyzable
2. **Log Levels**: Use appropriate log levels (INFO, WARNING, ERROR) to distinguish between different types of log entries
3. **Correlation IDs**: Include correlation IDs in logs to track requests across multiple services
4. **Sensitive Data**: Avoid logging sensitive data such as authentication tokens or personal information
5. **Regular Review**: Regularly review logs and metrics to identify potential issues before they become critical
6. **Alert Tuning**: Regularly review and tune alert thresholds based on actual system behavior
7. **Documentation**: Keep alert runbooks updated with troubleshooting steps for each alert type
8. **Escalation**: Set up proper escalation procedures for critical alerts
9. **Testing**: Regularly test alerting policies to ensure they work correctly
10. **Cost Monitoring**: Monitor costs associated with logging and monitoring to optimize resource usage

## Cost Optimization

1. **Log Retention**: Set appropriate log retention periods to balance cost and compliance requirements
2. **Log Filtering**: Use log filters to reduce the volume of logs being stored
3. **Custom Metrics**: Limit the number of custom metrics to avoid excessive costs
4. **Alert Frequency**: Set reasonable alert thresholds to avoid alert fatigue
5. **Dashboard Optimization**: Limit the number of widgets on dashboards to reduce query costs
