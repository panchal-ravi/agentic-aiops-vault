# Data Model: AWS CloudWatch Logs Filter MCP Tool

**Date**: 22 October 2025  
**Phase**: 1 - Design & Contracts

## Core Entities

### LogEvent

Represents an individual log entry from CloudWatch Logs.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class LogEvent:
    """Individual log entry with timestamp, message content, log level, and metadata."""
    
    # Required fields
    timestamp: datetime          # Event timestamp (converted from Unix milliseconds)
    message: str                # Raw log message content
    log_stream_name: str        # Source log stream identifier
    
    # Optional fields
    log_level: Optional[str] = None     # Extracted log level (ERROR, WARN, INFO, DEBUG)
    event_id: Optional[str] = None      # CloudWatch event ID for deduplication
    ingestion_time: Optional[datetime] = None  # CloudWatch ingestion timestamp
    
    # Metadata fields
    metadata: Dict[str, Any] = None     # Additional parsed fields (JSON, key-value pairs)
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "log_stream_name": self.log_stream_name,
            "log_level": self.log_level,
            "event_id": self.event_id,
            "ingestion_time": self.ingestion_time.isoformat() if self.ingestion_time else None,
            "metadata": self.metadata
        }
```

**Validation Rules**:
- `timestamp` must be valid datetime
- `message` cannot be empty string
- `log_stream_name` must match AWS naming conventions
- `log_level` must be one of: ERROR, WARN, INFO, DEBUG, or None

### FilterCriteria

Defines parameters for filtering log events.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Pattern
import re

@dataclass
class FilterCriteria:
    """Parameters defining what events to include in filter results."""
    
    # Time range filtering
    start_time: Optional[datetime] = None    # Filter events after this time
    end_time: Optional[datetime] = None      # Filter events before this time
    
    # Text pattern filtering
    text_pattern: Optional[str] = None       # Simple text search
    regex_pattern: Optional[Pattern] = None  # Compiled regex pattern
    filter_pattern: Optional[str] = None     # CloudWatch filter pattern syntax
    
    # Log level filtering
    log_levels: Optional[List[str]] = None   # List of log levels to include
    
    # Stream/group targeting
    log_group_name: str                      # Target CloudWatch log group
    log_stream_names: Optional[List[str]] = None  # Specific streams (None = all streams)
    
    # Result control
    max_events: int = 1000                   # Maximum events to return
    start_from_head: bool = True             # Direction of search
    
    def __post_init__(self):
        """Validate and normalize filter criteria."""
        # Validate time range
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        
        # Compile regex pattern if provided
        if isinstance(self.regex_pattern, str):
            try:
                self.regex_pattern = re.compile(self.regex_pattern, re.IGNORECASE)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        
        # Normalize log levels
        if self.log_levels:
            valid_levels = {"ERROR", "WARN", "INFO", "DEBUG"}
            self.log_levels = [level.upper() for level in self.log_levels]
            invalid_levels = set(self.log_levels) - valid_levels
            if invalid_levels:
                raise ValueError(f"Invalid log levels: {invalid_levels}")
        
        # Validate max_events
        if self.max_events <= 0:
            raise ValueError("max_events must be positive")
        if self.max_events > 10000:
            raise ValueError("max_events cannot exceed 10000")
    
    def to_cloudwatch_params(self) -> Dict[str, Any]:
        """Convert to CloudWatch filter_log_events parameters."""
        params = {
            "logGroupName": self.log_group_name,
            "startFromHead": self.start_from_head,
            "limit": min(self.max_events, 1000)  # CloudWatch API limit
        }
        
        if self.log_stream_names:
            params["logStreamNames"] = self.log_stream_names
        
        if self.start_time:
            params["startTime"] = int(self.start_time.timestamp() * 1000)
        
        if self.end_time:
            params["endTime"] = int(self.end_time.timestamp() * 1000)
        
        if self.filter_pattern:
            params["filterPattern"] = self.filter_pattern
        
        return params
```

**State Transitions**:
- Created → Validated → Executed → Completed
- Can be reused for multiple queries with same parameters

### QueryResults

Represents the result set from a log filtering operation.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any

@dataclass
class QueryResults:
    """Filtered collection of log events with metadata about query execution."""
    
    # Core results
    events: List[LogEvent]               # Filtered log events
    total_events: int                    # Total events found (may exceed returned count)
    
    # Query metadata
    query_id: str                        # Unique identifier for this query
    execution_time_ms: float            # Query execution duration
    start_time: datetime                 # Query start timestamp
    end_time: datetime                   # Query completion timestamp
    
    # Pagination support
    next_token: Optional[str] = None     # Token for next page of results
    has_more_events: bool = False        # Whether additional events available
    
    # Source information
    log_group_name: str                  # Source log group
    log_streams_queried: List[str]       # List of streams included in query
    
    # Filter statistics
    events_scanned: int = 0              # Total events examined
    events_matched: int = 0              # Events matching filter criteria
    api_calls_made: int = 0              # Number of CloudWatch API calls
    
    # Error tracking
    errors: List[str] = None             # Non-fatal errors encountered
    warnings: List[str] = None           # Warnings about query execution
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []
        
        # Update matched count to actual events returned
        self.events_matched = len(self.events)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "events": [event.to_dict() for event in self.events],
            "total_events": self.total_events,
            "query_metadata": {
                "query_id": self.query_id,
                "execution_time_ms": self.execution_time_ms,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "next_token": self.next_token,
                "has_more_events": self.has_more_events
            },
            "source_information": {
                "log_group_name": self.log_group_name,
                "log_streams_queried": self.log_streams_queried
            },
            "statistics": {
                "events_scanned": self.events_scanned,
                "events_matched": self.events_matched,
                "api_calls_made": self.api_calls_made
            },
            "issues": {
                "errors": self.errors,
                "warnings": self.warnings
            }
        }
    
    def add_error(self, error: str):
        """Add an error message to the results."""
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        """Add a warning message to the results."""
        self.warnings.append(warning)
```

## Supporting Data Types

### CloudWatchCredentials

Configuration for AWS authentication.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class CloudWatchCredentials:
    """AWS authentication configuration for CloudWatch access."""
    
    region_name: str                           # AWS region for CloudWatch API
    access_key_id: Optional[str] = None        # AWS access key (if not using IAM roles)
    secret_access_key: Optional[str] = None    # AWS secret key (if not using IAM roles)
    session_token: Optional[str] = None        # Temporary session token (for STS)
    profile_name: Optional[str] = None         # AWS CLI profile name
    
    def __post_init__(self):
        """Validate credential configuration."""
        if not self.region_name:
            raise ValueError("region_name is required")
        
        # If access keys provided, both must be present
        if self.access_key_id or self.secret_access_key:
            if not (self.access_key_id and self.secret_access_key):
                raise ValueError("Both access_key_id and secret_access_key required")
```

### LogStreamInfo

Metadata about CloudWatch log streams.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class LogStreamInfo:
    """Metadata about a CloudWatch log stream."""
    
    log_stream_name: str                    # Stream name
    log_group_name: str                     # Parent log group
    creation_time: datetime                 # Stream creation timestamp
    last_event_time: Optional[datetime]     # Most recent event timestamp
    last_ingestion_time: Optional[datetime] # Most recent ingestion timestamp
    upload_sequence_token: Optional[str]    # Current sequence token
    arn: Optional[str]                      # Stream ARN
    stored_bytes: Optional[int]             # Approximate size in bytes
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "log_stream_name": self.log_stream_name,
            "log_group_name": self.log_group_name,
            "creation_time": self.creation_time.isoformat(),
            "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None,
            "last_ingestion_time": self.last_ingestion_time.isoformat() if self.last_ingestion_time else None,
            "upload_sequence_token": self.upload_sequence_token,
            "arn": self.arn,
            "stored_bytes": self.stored_bytes
        }
```

## Relationships

```text
FilterCriteria ---> QueryResults
    |                    |
    |                    v
    |               LogEvent[]
    |                    |
    v                    |
CloudWatchCredentials    |
    |                    |
    v                    v
LogStreamInfo <----- LogEvent
```

**Key Relationships**:
- `FilterCriteria` defines the query parameters for log filtering
- `QueryResults` contains the filtered `LogEvent` collection
- `LogEvent` references source `LogStreamInfo` via `log_stream_name`
- `CloudWatchCredentials` provides authentication for accessing log data
- `QueryResults` tracks execution metadata and supports pagination

## Data Validation

All entities implement comprehensive validation:

1. **Input Validation**: Parameter types, ranges, and formats
2. **Business Rules**: Log level validity, time range logic, AWS naming conventions
3. **Security Validation**: Pattern injection prevention, credential masking
4. **Performance Constraints**: Maximum result sizes, timeout limits

## JSON Schema Compliance

All data models support JSON serialization through `to_dict()` methods that produce consistent, documented schemas suitable for MCP tool responses and API contracts.