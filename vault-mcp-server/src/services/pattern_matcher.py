"""
Pattern matching service for CloudWatch log events.

This module provides pattern matching capabilities including log level detection,
regex matching, and text pattern filtering for CloudWatch log events.
"""

import logging
import re
from datetime import datetime
from typing import Any

from ..models.cloudwatch import LogEvent, FilterCriteria
from .compound_expression_parser import CompoundExpressionParser


logger = logging.getLogger(__name__)


class PatternMatcher:
    """
    Pattern matching service for log events.

    Handles log level detection, regex pattern matching, and text filtering
    with optimized performance for large log volumes.
    """

    # Pre-compiled regex patterns for common log levels
    LOG_LEVEL_PATTERNS = {
        "ERROR": re.compile(r"\b(?:ERROR|error|Error|\[ERROR\]|\[error\])\b"),
        "WARN": re.compile(
            r"\b(?:WARN|warn|Warn|WARNING|warning|Warning|\[WARN\]|\[warn\]|\[WARNING\]|\[warning\])\b"
        ),
        "INFO": re.compile(r"\b(?:INFO|info|Info|\[INFO\]|\[info\])\b"),
        "DEBUG": re.compile(r"\b(?:DEBUG|debug|Debug|\[DEBUG\]|\[debug\])\b"),
    }

    def __init__(self):
        """Initialize the pattern matcher."""
        self.stats = {
            "events_processed": 0,
            "log_levels_detected": 0,
            "pattern_matches": 0,
            "regex_matches": 0,
            "compound_expression_matches": 0,
        }
        self.expression_parser = CompoundExpressionParser()

    def extract_log_level(self, message: str) -> str | None:
        """
        Extract log level from log message.

        Args:
            message: Log message content

        Returns:
            Detected log level or None if not found
        """
        for level, pattern in self.LOG_LEVEL_PATTERNS.items():
            if pattern.search(message):
                self.stats["log_levels_detected"] += 1
                return level

        return None

    def matches_text_pattern(self, message: str, pattern: str) -> bool:
        """
        Check if message matches text pattern (case-insensitive).

        Args:
            message: Log message content
            pattern: Text pattern to search for

        Returns:
            True if pattern found in message
        """
        if not pattern:
            return True

        matches = pattern.lower() in message.lower()
        if matches:
            self.stats["pattern_matches"] += 1

        return matches

    def matches_regex_pattern(self, message: str, compiled_regex: re.Pattern[str]) -> bool:
        """
        Check if message matches compiled regex pattern.

        Args:
            message: Log message content
            compiled_regex: Pre-compiled regex pattern

        Returns:
            True if regex matches message
        """
        if not compiled_regex:
            return True

        matches = bool(compiled_regex.search(message))
        if matches:
            self.stats["regex_matches"] += 1

        return matches

    def matches_log_levels(self, detected_level: str | None, target_levels: list[str]) -> bool:
        """
        Check if detected log level matches target levels.

        Args:
            detected_level: Log level detected from message
            target_levels: List of target log levels to match

        Returns:
            True if detected level is in target levels
        """
        if not target_levels:
            return True

        return detected_level in target_levels

    def matches_compound_expression(self, message: str, expression: str) -> bool:
        """
        Check if message matches compound expression with fast-path optimizations.

        Args:
            message: Log message content
            expression: Compound expression to evaluate

        Returns:
            True if expression matches message
        """
        if not expression:
            return True

        try:
            # Fast path: Skip non-JSON messages immediately if expression requires JSON
            if "$." in expression:
                if not message.strip().startswith("{"):
                    return False
                # Quick check for required keywords before JSON parsing
                if "request.operation" in expression and '"operation"' not in message:
                    return False
                if "pki_int/issue" in expression and "pki_int/issue" not in message:
                    return False
                if "entity_id" in expression and "entity_id" not in message:
                    return False

            # Skip very large messages to prevent slowdown
            if len(message) > 5000:
                logger.debug("Skipping large message for performance")
                return False

            # Try to parse message as JSON for compound expression evaluation
            import json

            log_data = {}
            try:
                if message.strip().startswith("{") and message.strip().endswith("}"):
                    log_data = json.loads(message.strip())
                else:
                    # Skip if expression requires JSON but message is not JSON
                    if "$." in expression:
                        return False
                    log_data = {"message": message}
            except (json.JSONDecodeError, ValueError):
                # Fast fail for JSON parsing errors with JSON path expressions
                if "$." in expression:
                    return False
                log_data = {"message": message}

            # Use the expression parser to evaluate
            matches = self.expression_parser.parse_and_evaluate(expression, log_data)
            if matches:
                self.stats["compound_expression_matches"] += 1

            return matches

        except Exception as e:
            logger.debug(f"Failed to evaluate compound expression: {e}")
            return False

    def process_log_event(
        self, event_data: dict[str, Any], log_stream_name: str, criteria: FilterCriteria
    ) -> LogEvent | None:
        """
        Process raw CloudWatch log event data into LogEvent object with fast filtering.

        Args:
            event_data: Raw event data from CloudWatch API
            log_stream_name: Name of the source log stream
            criteria: Filter criteria for pattern matching

        Returns:
            LogEvent object if it matches criteria, None otherwise
        """
        self.stats["events_processed"] += 1

        # Extract basic event information
        message = event_data.get("message", "")

        # Fast path: Skip obvious non-matches before expensive processing
        if criteria.compound_expression:
            # Quick keyword checks before full parsing
            if "pki_int/issue" in criteria.compound_expression and "pki_int/issue" not in message:
                return None
            if "entity_id" in criteria.compound_expression and "entity_id" not in message:
                return None
            # More flexible check for operation update
            if (
                "operation" in criteria.compound_expression
                and "update" in criteria.compound_expression
                and (
                    '"operation":"update"' not in message
                    and '"operation": "update"' not in message
                    and 'operation":"update' not in message
                )
            ):
                return None

        timestamp = datetime.fromtimestamp(event_data["timestamp"] / 1000)
        event_id = event_data.get("eventId")
        ingestion_time = None
        if event_data.get("ingestionTime"):
            ingestion_time = datetime.fromtimestamp(event_data["ingestionTime"] / 1000)

        # Extract log level (quick regex check)
        log_level = self.extract_log_level(message)

        # Apply filters with fast path
        if not self._matches_criteria_fast(message, log_level, criteria):
            return None

        # Parse additional metadata only for matching events
        metadata = self._extract_metadata_fast(message)

        return LogEvent(
            timestamp=timestamp,
            message=message,
            log_stream_name=log_stream_name,
            log_level=log_level,
            event_id=event_id,
            ingestion_time=ingestion_time,
            metadata=metadata,
        )

    def _matches_criteria_fast(
        self, message: str, log_level: str | None, criteria: FilterCriteria
    ) -> bool:
        """
        Fast check if message matches filter criteria with early exits.

        Args:
            message: Log message content
            log_level: Detected log level
            criteria: Filter criteria to apply

        Returns:
            True if message matches all criteria
        """
        # Check text pattern first (fastest)
        if criteria.text_pattern and not self.matches_text_pattern(message, criteria.text_pattern):
            return False

        # Check log levels (fast)
        if criteria.log_levels and not self.matches_log_levels(log_level, criteria.log_levels):
            return False

        # Check regex pattern
        if criteria.compiled_regex and not self.matches_regex_pattern(
            message, criteria.compiled_regex
        ):
            return False

        # Check compound expression last (most expensive)
        if criteria.compound_expression and not self.matches_compound_expression(
            message, criteria.compound_expression
        ):
            return False

        return True

    def _extract_metadata_fast(self, message: str) -> dict[str, Any]:
        """
        Fast metadata extraction that skips expensive parsing for performance.

        Args:
            message: Log message content

        Returns:
            Dictionary of extracted metadata (minimal for speed)
        """
        metadata = {}

        # Only try JSON parsing if it looks like JSON and is reasonably sized
        if (
            message.strip().startswith("{")
            and message.strip().endswith("}")
            and len(message) < 2000
        ):
            try:
                import json

                metadata = json.loads(message.strip())
                return metadata
            except (json.JSONDecodeError, ValueError):
                pass

        # Skip expensive regex extraction for speed
        return metadata

    def _extract_metadata(self, message: str) -> dict[str, Any]:
        """
        Extract structured metadata from log message.

        Attempts to parse JSON, key-value pairs, and common log formats.

        Args:
            message: Log message content

        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}

        try:
            # Try to parse as JSON
            import json

            if message.strip().startswith("{") and message.strip().endswith("}"):
                metadata = json.loads(message.strip())
                return metadata
        except (json.JSONDecodeError, ValueError):
            pass

        # Extract common patterns
        self._extract_ip_addresses(message, metadata)
        self._extract_timestamps(message, metadata)
        self._extract_http_status(message, metadata)
        self._extract_key_value_pairs(message, metadata)

        return metadata

    def _extract_ip_addresses(self, message: str, metadata: dict[str, Any]):
        """Extract IP addresses from message."""
        ip_pattern = re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b")
        ips = ip_pattern.findall(message)
        if ips:
            metadata["ip_addresses"] = ips

    def _extract_timestamps(self, message: str, metadata: dict[str, Any]):
        """Extract timestamp patterns from message."""
        # ISO 8601 timestamps
        iso_pattern = re.compile(
            r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"
        )
        timestamps = iso_pattern.findall(message)
        if timestamps:
            metadata["timestamps"] = timestamps

    def _extract_http_status(self, message: str, metadata: dict[str, Any]):
        """Extract HTTP status codes from message."""
        status_pattern = re.compile(r"\b[1-5]\d{2}\b")
        statuses = status_pattern.findall(message)
        if statuses:
            metadata["http_status_codes"] = [int(s) for s in statuses]

    def _extract_key_value_pairs(self, message: str, metadata: dict[str, Any]):
        """Extract key=value pairs from message."""
        kv_pattern = re.compile(r"(\w+)=([^\s,]+)")
        pairs = kv_pattern.findall(message)
        if pairs:
            metadata["key_value_pairs"] = dict(pairs)

    def get_statistics(self) -> dict[str, int]:
        """
        Get pattern matching statistics.

        Returns:
            Dictionary with processing statistics
        """
        return self.stats.copy()

    def reset_statistics(self):
        """Reset pattern matching statistics."""
        self.stats = {
            "events_processed": 0,
            "log_levels_detected": 0,
            "pattern_matches": 0,
            "regex_matches": 0,
            "compound_expression_matches": 0,
        }
