# Research: AWS CloudWatch Logs Filter MCP Tool

**Date**: 22 October 2025  
**Phase**: 0 - Research & Architecture  

## Research Tasks Completed

### AWS CloudWatch Logs API Integration

**Decision**: Use boto3 CloudWatch Logs client with filter_log_events API  
**Rationale**: 
- Native AWS SDK provides comprehensive CloudWatch Logs functionality
- filter_log_events API supports text patterns, time ranges, and pagination
- Built-in retry mechanisms and error handling for AWS API failures
- Supports IAM role-based authentication with fallback to environment variables

**Alternatives considered**:
- AWS CLI wrapper: Rejected due to subprocess complexity and error handling challenges
- Direct HTTP requests to CloudWatch API: Rejected due to authentication complexity and lack of built-in retry logic
- Third-party AWS libraries: Rejected due to additional dependencies and maintenance concerns

### Pattern Matching Implementation

**Decision**: Combine CloudWatch native filtering with Python regex for advanced patterns  
**Rationale**:
- CloudWatch filter_log_events supports basic text patterns natively (efficient server-side filtering)
- Python re module provides robust regex support for complex patterns
- Hybrid approach optimizes performance by reducing data transfer for basic filters

**Alternatives considered**:
- Client-side only filtering: Rejected due to performance impact on large log streams
- CloudWatch patterns only: Rejected due to limited regex support in CloudWatch

### Authentication Strategy

**Decision**: AWS IAM role-based authentication with environment variable fallback  
**Rationale**:
- Follows AWS security best practices
- boto3 credential chain automatically handles IAM roles, environment variables, and profiles
- Supports both development and production deployment scenarios

**Implementation approach**:
```python
# boto3 automatically handles credential chain:
# 1. IAM roles for EC2/Lambda
# 2. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
# 3. AWS credential files
# 4. IAM roles for cross-account access
client = boto3.client('logs', region_name=region)
```

### Error Handling and Retry Strategy

**Decision**: Implement exponential backoff with 3 retry attempts  
**Rationale**:
- AWS APIs can experience temporary failures or rate limiting
- Exponential backoff prevents overwhelming the API during recovery
- 3 retries balance reliability with response time requirements

**Implementation pattern**:
```python
from botocore.exceptions import ClientError
import time
import random

max_retries = 3
base_delay = 1

for attempt in range(max_retries):
    try:
        # CloudWatch API call
        break
    except ClientError as e:
        if attempt == max_retries - 1:
            raise
        delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
        time.sleep(delay)
```

### Pagination Strategy

**Decision**: Use CloudWatch pagination with 100 events per batch  
**Rationale**:
- CloudWatch filter_log_events supports pagination with nextToken
- 100 events per batch balances memory usage with API efficiency
- Matches requirement specification for batch size

**Implementation approach**:
```python
paginator = client.get_paginator('filter_log_events')
page_iterator = paginator.paginate(
    logGroupName=log_group,
    logStreamNames=[log_stream],
    filterPattern=pattern,
    PaginationConfig={'PageSize': 100}
)
```

### Log Level Detection

**Decision**: Regex-based log level extraction with configurable patterns  
**Rationale**:
- CloudWatch doesn't enforce log level structure
- Applications use various log level formats (INFO, info, [INFO], etc.)
- Regex patterns provide flexibility for different log formats

**Supported patterns**:
- Standard: `ERROR`, `WARN`, `INFO`, `DEBUG`
- Bracketed: `[ERROR]`, `[WARN]`, `[INFO]`, `[DEBUG]`
- Lowercase: `error`, `warn`, `info`, `debug`
- Timestamp prefixed: `2023-10-22 10:30:45 ERROR`

### Performance Optimization

**Decision**: Implement streaming processing with memory-efficient iteration  
**Rationale**:
- Large log streams can contain millions of events
- Streaming prevents memory exhaustion
- Generator-based processing enables real-time filtering

**Key optimizations**:
- Use boto3 paginators for memory-efficient iteration
- Process events in batches rather than loading all into memory
- Early termination for time-bounded queries
- Parallel processing for multi-stream queries

### Time Range Handling

**Decision**: Use AWS CloudWatch timestamp filtering with Python datetime validation  
**Rationale**:
- CloudWatch filter_log_events accepts startTime/endTime parameters (Unix timestamps)
- Server-side filtering reduces data transfer
- Python datetime provides flexible input format support

**Supported time formats**:
- ISO 8601: `2023-10-22T10:30:45Z`
- Unix timestamp: `1698056245`
- Relative: `1h`, `30m`, `2d` (converted to absolute timestamps)

## Best Practices Identified

### AWS CloudWatch Logs Best Practices

1. **Regional Configuration**: Always specify AWS region explicitly
2. **Credential Management**: Use IAM roles in production, environment variables for development
3. **API Limits**: Respect CloudWatch API throttling (5 requests per second per account)
4. **Cost Optimization**: Use filterPattern to reduce data processing charges
5. **Monitoring**: Log API usage for debugging and optimization

### MCP Tool Design Best Practices

1. **Function Signatures**: Follow exact MCP protocol patterns with type annotations
2. **Documentation**: Comprehensive docstrings with examples for LLM consumption
3. **Error Responses**: Structured error objects with success/failure indicators
4. **Input Validation**: Schema validation on all parameters before AWS API calls
5. **Async/Await**: Use async functions for non-blocking I/O operations

### Security Best Practices

1. **Token Validation**: Validate AWS credentials before making API calls
2. **Input Sanitization**: Escape regex patterns to prevent injection attacks
3. **Audit Logging**: Log all filter operations for security monitoring
4. **Error Masking**: Don't expose AWS account details in error messages
5. **Principle of Least Privilege**: Request minimal CloudWatch permissions

## Architecture Decisions

### Component Structure

```text
CloudWatch Client (services/cloudwatch_client.py)
├── Authentication handling
├── Region configuration
├── API retry logic
└── Connection management

Log Filter (services/log_filter.py)
├── Filter criteria parsing
├── CloudWatch API orchestration
├── Result aggregation
└── Pagination handling

Pattern Matcher (services/pattern_matcher.py)
├── Regex compilation and validation
├── Log level detection
├── Text pattern matching
└── Performance optimization

MCP Tools (tools/)
├── filter_logs.py - Primary filtering tool
├── list_log_groups.py - Discovery tool
└── list_log_streams.py - Discovery tool
```

### Data Flow

1. **Input Validation**: MCP tool validates parameters and converts to internal format
2. **Filter Preparation**: Pattern compilation and time range conversion
3. **CloudWatch Query**: API calls with pagination and retry logic
4. **Result Processing**: Pattern matching and log level extraction
5. **Response Formatting**: Structured JSON response with metadata

This research provides the foundation for implementing a robust, secure, and performant CloudWatch Logs filtering MCP tool that meets all specified requirements.