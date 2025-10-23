"""
CloudWatch Logs data models for MCP tools.

This module defines the data structures used for CloudWatch Logs filtering operations,
including log events, filter criteria, and query results.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import re
import uuid


@dataclass
class LogEvent:
    """Individual log entry with timestamp, message content, log level, and metadata."""

    # Required fields
    timestamp: datetime  # Event timestamp (converted from Unix milliseconds)
    message: str  # Raw log message content
    log_stream_name: str  # Source log stream identifier

    # Optional fields
    log_level: str | None = None  # Extracted log level (ERROR, WARN, INFO, DEBUG)
    event_id: str | None = None  # CloudWatch event ID for deduplication
    ingestion_time: datetime | None = None  # CloudWatch ingestion timestamp

    # Metadata fields
    metadata: dict[str, Any] = field(default_factory=dict)  # Additional parsed fields

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "log_stream_name": self.log_stream_name,
            "log_level": self.log_level,
            "event_id": self.event_id,
            "ingestion_time": self.ingestion_time.isoformat() if self.ingestion_time else None,
            "metadata": self.metadata,
        }


@dataclass
class FilterCriteria:
    """Parameters defining what events to include in filter results."""

    # Stream/group targeting
    log_group_name: str  # Target CloudWatch log group
    log_stream_names: list[str] | None = None  # Specific streams (None = all streams)

    # Time range filtering
    start_time: datetime | None = None  # Filter events after this time
    end_time: datetime | None = None  # Filter events before this time

    # Text pattern filtering
    text_pattern: str | None = None  # Simple text search
    regex_pattern: str | None = None  # Regex pattern string
    filter_pattern: str | None = None  # CloudWatch filter pattern syntax

    # Log level filtering
    log_levels: list[str] | None = None  # List of log levels to include

    # Result control
    max_events: int = 1000  # Maximum events to return
    start_from_head: bool = True  # Direction of search
    next_token: str | None = None  # Pagination token

    # Compiled patterns (set during validation)
    _compiled_regex: re.Pattern[str] | None = field(default=None, init=False)

    def __post_init__(self):
        """Validate and normalize filter criteria."""
        # Validate required fields
        if not self.log_group_name:
            raise ValueError("log_group_name is required")

        # Validate time range
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")

        # Compile regex pattern if provided
        if self.regex_pattern:
            try:
                self._compiled_regex = re.compile(self.regex_pattern, re.IGNORECASE)
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

    @property
    def compiled_regex(self) -> re.Pattern[str] | None:
        """Get compiled regex pattern."""
        return self._compiled_regex

    def to_cloudwatch_params(self) -> dict[str, Any]:
        """Convert to CloudWatch filter_log_events parameters."""
        params = {
            "logGroupName": self.log_group_name,
            "limit": min(self.max_events, 1000),  # CloudWatch API limit per call
        }

        if self.log_stream_names:
            params["logStreamNames"] = self.log_stream_names

        if self.start_time:
            params["startTime"] = int(self.start_time.timestamp() * 1000)

        if self.end_time:
            params["endTime"] = int(self.end_time.timestamp() * 1000)

        if self.filter_pattern:
            params["filterPattern"] = self.filter_pattern

        if self.next_token:
            params["nextToken"] = self.next_token

        return params


@dataclass
class QueryResults:
    """Filtered collection of log events with metadata about query execution."""

    # Core results
    events: list[LogEvent]  # Filtered log events
    total_events: int  # Total events found (may exceed returned count)

    # Query metadata
    query_id: str  # Unique identifier for this query
    execution_time_ms: float  # Query execution duration
    start_time: datetime  # Query start timestamp
    end_time: datetime  # Query completion timestamp

    # Source information (required fields)
    log_group_name: str  # Source log group

    # Pagination support (optional fields)
    next_token: str | None = None  # Token for next page of results
    has_more_events: bool = False  # Whether additional events available

    # Optional metadata
    log_streams_queried: list[str] = field(default_factory=list)  # Streams included

    # Filter statistics
    events_scanned: int = 0  # Total events examined
    events_matched: int = 0  # Events matching filter criteria
    api_calls_made: int = 0  # Number of CloudWatch API calls

    # Error tracking
    errors: list[str] = field(default_factory=list)  # Non-fatal errors
    warnings: list[str] = field(default_factory=list)  # Warnings about execution

    def __post_init__(self):
        # Update matched count to actual events returned
        self.events_matched = len(self.events)

        # Generate query ID if not provided
        if not hasattr(self, "query_id") or not self.query_id:
            self.query_id = f"q_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> dict[str, Any]:
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
                "has_more_events": self.has_more_events,
            },
            "source_information": {
                "log_group_name": self.log_group_name,
                "log_streams_queried": self.log_streams_queried,
            },
            "statistics": {
                "events_scanned": self.events_scanned,
                "events_matched": self.events_matched,
                "api_calls_made": self.api_calls_made,
            },
            "issues": {"errors": self.errors, "warnings": self.warnings},
        }

    def add_error(self, error: str):
        """Add an error message to the results."""
        self.errors.append(error)

    def add_warning(self, warning: str):
        """Add a warning message to the results."""
        self.warnings.append(warning)


@dataclass
class CloudWatchCredentials:
    """AWS authentication configuration for CloudWatch access."""

    region_name: str  # AWS region for CloudWatch API
    access_key_id: str | None = None  # AWS access key (if not using IAM roles)
    secret_access_key: str | None = None  # AWS secret key (if not using IAM roles)
    session_token: str | None = None  # Temporary session token (for STS)
    profile_name: str | None = None  # AWS CLI profile name

    def __post_init__(self):
        """Validate credential configuration."""
        if not self.region_name:
            raise ValueError("region_name is required")

        # If access keys provided, both must be present
        if self.access_key_id or self.secret_access_key:
            if not (self.access_key_id and self.secret_access_key):
                raise ValueError("Both access_key_id and secret_access_key required")


@dataclass
class LogStreamInfo:
    """Metadata about a CloudWatch log stream."""

    log_stream_name: str  # Stream name
    log_group_name: str  # Parent log group
    creation_time: datetime  # Stream creation timestamp
    last_event_time: datetime | None = None  # Most recent event timestamp
    last_ingestion_time: datetime | None = None  # Most recent ingestion timestamp
    upload_sequence_token: str | None = None  # Current sequence token
    arn: str | None = None  # Stream ARN
    stored_bytes: int | None = None  # Approximate size in bytes

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "log_stream_name": self.log_stream_name,
            "log_group_name": self.log_group_name,
            "creation_time": self.creation_time.isoformat(),
            "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None,
            "last_ingestion_time": self.last_ingestion_time.isoformat()
            if self.last_ingestion_time
            else None,
            "upload_sequence_token": self.upload_sequence_token,
            "arn": self.arn,
            "stored_bytes": self.stored_bytes,
        }


@dataclass
class LogGroupInfo:
    """Metadata about a CloudWatch log group."""

    log_group_name: str  # Log group name
    creation_time: datetime  # Group creation timestamp
    retention_in_days: int | None = None  # Log retention period
    metric_filter_count: int | None = None  # Number of metric filters
    arn: str | None = None  # Group ARN
    stored_bytes: int | None = None  # Approximate size in bytes
    kms_key_id: str | None = None  # KMS key for encryption

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "log_group_name": self.log_group_name,
            "creation_time": self.creation_time.isoformat(),
            "retention_in_days": self.retention_in_days,
            "metric_filter_count": self.metric_filter_count,
            "arn": self.arn,
            "stored_bytes": self.stored_bytes,
            "kms_key_id": self.kms_key_id,
        }
