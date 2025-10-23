# Quick Start Guide: AWS CloudWatch Logs Filter MCP Tool

**Date**: 22 October 2025  
**Feature**: AWS CloudWatch Logs Filter MCP Tool

## Overview

This MCP tool enables filtering and querying AWS CloudWatch log streams with advanced pattern matching, time range filtering, and log level classification. The tool integrates with existing vault-mcp-server and follows MCP protocol standards.

## Prerequisites

1. **AWS Account**: Valid AWS account with CloudWatch Logs access
2. **AWS Credentials**: Configured IAM role or environment variables
3. **Python Environment**: Python 3.11+ with uv package manager
4. **MCP Server**: Existing vault-mcp-server installation

## Required AWS Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:FilterLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
```

## Installation

### 1. Install Dependencies

Navigate to the vault-mcp-server directory and install required packages:

```bash
cd vault-mcp-server
uv add boto3 botocore
uv add --dev pytest-asyncio moto
```

### 2. Configure AWS Credentials

Choose one of the following authentication methods:

**Option A: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

**Option B: IAM Role (Recommended for production)**
```bash
# Ensure your EC2 instance or Lambda has appropriate IAM role
export AWS_DEFAULT_REGION=us-east-1
```

**Option C: AWS CLI Profile**
```bash
aws configure --profile cloudwatch-logs
export AWS_PROFILE=cloudwatch-logs
export AWS_DEFAULT_REGION=us-east-1
```

### 3. Verify Access

Test your CloudWatch access:

```bash
aws logs describe-log-groups --limit 5
```

## Basic Usage

### Starting the MCP Server

The CloudWatch tools are automatically registered when starting the vault-mcp-server:

```bash
python main.py
```

### Example 1: Basic Text Filtering

Filter logs containing "ERROR" from the last hour:

```python
import asyncio
from src.tools.filter_logs import filter_logs

async def example_basic_filter():
    result = await filter_logs({
        "log_group_name": "/aws/lambda/my-function",
        "text_pattern": "ERROR",
        "start_time": "2023-10-22T10:00:00Z",
        "end_time": "2023-10-22T11:00:00Z",
        "max_events": 100
    })
    
    print(f"Found {result['data']['total_events']} error events")
    for event in result['data']['events']:
        print(f"{event['timestamp']}: {event['message']}")

asyncio.run(example_basic_filter())
```

### Example 2: Advanced Pattern Matching

Use regex to find IP addresses in logs:

```python
async def example_regex_filter():
    result = await filter_logs({
        "log_group_name": "/aws/apigateway/access-logs",
        "regex_pattern": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
        "max_events": 50
    })
    
    print(f"Found {len(result['data']['events'])} events with IP addresses")
```

### Example 3: Log Level Filtering

Filter by specific log levels:

```python
async def example_log_level_filter():
    result = await filter_logs({
        "log_group_name": "/aws/ecs/my-service",
        "log_levels": ["ERROR", "WARN"],
        "start_time": "2023-10-22T00:00:00Z",
        "max_events": 200
    })
    
    print(f"Found {result['data']['total_events']} error/warning events")
```

### Example 4: Multi-Stream Filtering

Query specific log streams:

```python
async def example_multi_stream():
    result = await filter_logs({
        "log_group_name": "/aws/lambda/my-function",
        "log_stream_names": [
            "2023/10/22/[$LATEST]abc123",
            "2023/10/22/[$LATEST]def456"
        ],
        "text_pattern": "timeout",
        "max_events": 100
    })
    
    print(f"Found timeouts across {len(result['data']['source_information']['log_streams_queried'])} streams")
```

## Discovery Tools

### List Available Log Groups

```python
from src.tools.list_log_groups import list_log_groups

async def discover_log_groups():
    result = await list_log_groups({
        "prefix": "/aws/lambda/",
        "limit": 20
    })
    
    for group in result['data']['log_groups']:
        print(f"Log Group: {group['log_group_name']}")
        print(f"  Created: {group['creation_time']}")
        print(f"  Size: {group['stored_bytes']} bytes")
```

### List Log Streams in a Group

```python
from src.tools.list_log_streams import list_log_streams

async def discover_log_streams():
    result = await list_log_streams({
        "log_group_name": "/aws/lambda/my-function",
        "order_by": "LastEventTime",
        "descending": True,
        "limit": 10
    })
    
    for stream in result['data']['log_streams']:
        print(f"Stream: {stream['log_stream_name']}")
        print(f"  Last Event: {stream['last_event_time']}")
```

## Time Range Specifications

The tool supports multiple time formats:

```python
# ISO 8601 timestamp
"start_time": "2023-10-22T10:30:45Z"

# Unix timestamp (will be converted)
"start_time": 1698056245

# Relative time (implemented in client)
# "1h" = 1 hour ago
# "30m" = 30 minutes ago  
# "2d" = 2 days ago
```

## Performance Optimization

### Efficient Filtering

1. **Use CloudWatch patterns first**: More efficient than client-side regex
2. **Limit time ranges**: Reduce data transfer with specific start/end times
3. **Specify streams**: Query specific streams instead of entire log group
4. **Reasonable limits**: Use appropriate max_events values

```python
# Efficient approach
result = await filter_logs({
    "log_group_name": "/aws/lambda/my-function",
    "log_stream_names": ["2023/10/22/[$LATEST]abc123"],  # Specific stream
    "filter_pattern": "ERROR",                            # CloudWatch pattern
    "start_time": "2023-10-22T10:00:00Z",               # Limited time range
    "end_time": "2023-10-22T11:00:00Z",
    "max_events": 100                                     # Reasonable limit
})
```

### Pagination for Large Results

```python
async def paginated_query():
    next_token = None
    all_events = []
    
    while True:
        result = await filter_logs({
            "log_group_name": "/aws/lambda/my-function",
            "text_pattern": "ERROR",
            "max_events": 100,
            "next_token": next_token  # Continue from previous page
        })
        
        all_events.extend(result['data']['events'])
        
        if not result['data']['query_metadata']['has_more_events']:
            break
            
        next_token = result['data']['query_metadata']['next_token']
    
    print(f"Retrieved {len(all_events)} total events")
```

## Error Handling

### Common Error Scenarios

1. **Authentication Failures**
```python
# Error response
{
    "success": false,
    "message": "AWS authentication failed",
    "error_code": "AUTH_FAILED",
    "details": {
        "aws_error": "InvalidUserID.NotFound"
    }
}
```

2. **Resource Not Found**
```python
# Error response
{
    "success": false,
    "message": "Log group not found",
    "error_code": "RESOURCE_NOT_FOUND",
    "details": {
        "resource": "/aws/lambda/nonexistent-function"
    }
}
```

3. **Rate Limiting**
```python
# Error response
{
    "success": false,
    "message": "AWS API rate limit exceeded",
    "error_code": "RATE_LIMITED",
    "details": {
        "retry_after": 30
    }
}
```

### Retry Logic

The tool automatically implements exponential backoff for transient failures:

```python
# Automatic retry for:
# - Network timeouts
# - AWS throttling
# - Temporary service unavailability

# Manual retry for rate limits
import asyncio

async def retry_with_backoff():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = await filter_logs(criteria)
            return result
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
```

## Testing Your Setup

### Unit Test

```python
# tests/unit/test_cloudwatch_integration.py
import pytest
from src.tools.filter_logs import filter_logs

@pytest.mark.asyncio
async def test_basic_filtering():
    result = await filter_logs({
        "log_group_name": "/aws/lambda/test-function",
        "text_pattern": "test",
        "max_events": 10
    })
    
    assert result['success'] == True
    assert 'events' in result['data']
    assert len(result['data']['events']) <= 10
```

### Integration Test

```python
@pytest.mark.asyncio
async def test_end_to_end_filtering():
    # Requires actual AWS access
    result = await filter_logs({
        "log_group_name": "/aws/lambda/your-actual-function",
        "start_time": "2023-10-22T00:00:00Z",
        "max_events": 5
    })
    
    assert result['success'] == True
    assert result['data']['query_metadata']['execution_time_ms'] < 10000
```

## Troubleshooting

### Common Issues

1. **"Log group not found"**
   - Verify log group name exists: `aws logs describe-log-groups`
   - Check AWS region configuration

2. **"Authentication failed"**
   - Verify AWS credentials: `aws sts get-caller-identity`
   - Check IAM permissions for CloudWatch Logs

3. **"No events found"**
   - Verify time range includes actual log events
   - Check if log streams have recent activity
   - Test with broader filter criteria

4. **Performance issues**
   - Reduce time range scope
   - Use more specific filter patterns
   - Query specific log streams instead of entire group

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Run your filter operation
result = await filter_logs(criteria)
```

## Next Steps

1. **Explore Advanced Patterns**: Learn regex patterns for your specific log formats
2. **Set Up Monitoring**: Monitor API usage and costs in AWS CloudWatch
3. **Optimize Queries**: Profile your most common queries for performance
4. **Automate Workflows**: Integrate with alerting systems or log analysis pipelines

## Support

- **Issues**: Report problems with specific error messages and query parameters
- **Performance**: Include query execution times and data volumes
- **Authentication**: Verify AWS credentials and permissions separately

This quick start guide provides the foundation for using CloudWatch Logs filtering effectively within the MCP framework.