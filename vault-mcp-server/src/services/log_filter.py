"""
Log filtering service for CloudWatch Logs.

This module orchestrates CloudWatch API calls, pattern matching, and result
aggregation to provide comprehensive log filtering capabilities.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

from ..models.cloudwatch import FilterCriteria, QueryResults
from .cloudwatch_client import CloudWatchClient
from .pattern_matcher import PatternMatcher


logger = logging.getLogger(__name__)


class LogFilter:
    """
    Main log filtering service.

    Orchestrates CloudWatch API calls, pattern matching, and result processing
    to provide comprehensive log filtering with pagination and error handling.
    """

    def __init__(self, cloudwatch_client: CloudWatchClient | None = None):
        """
        Initialize log filter service.

        Args:
            cloudwatch_client: CloudWatch client instance. If None, creates new one.
        """
        self.cloudwatch_client = cloudwatch_client or CloudWatchClient()
        self.pattern_matcher = PatternMatcher()

    async def filter_logs(self, criteria: FilterCriteria) -> QueryResults:
        """
        Filter CloudWatch log events using server-side filtering.

        CloudWatch's filterPattern does the filtering server-side,
        so we just retrieve and format the results.

        Args:
            criteria: Filter criteria including patterns, time ranges, and targets

        Returns:
            QueryResults with filtered events and execution metadata
        """
        start_time = datetime.now()
        query_id = f"q_{uuid.uuid4().hex[:8]}"

        # Initialize result tracking
        all_events = []
        api_calls_made = 0
        events_scanned = 0
        errors = []
        warnings = []

        logger.info(f"Starting log filter query {query_id} for group: {criteria.log_group_name}")

        try:
            # Get target log streams if not specified
            target_streams = criteria.log_stream_names
            if not target_streams:
                target_streams = await self._get_active_log_streams(
                    criteria.log_group_name, limit=10
                )
                if not target_streams:
                    warnings.append(f"No active log streams found in {criteria.log_group_name}")
                    return self._create_empty_result(
                        query_id, start_time, criteria, warnings, errors
                    )

            # Make CloudWatch API call with server-side filtering
            # CloudWatch will do the pattern matching for us
            next_token = criteria.next_token
            events_collected = 0
            max_iterations = 100  # Limit iterations for safety

            for iteration in range(max_iterations):
                try:
                    response = await asyncio.wait_for(
                        self.cloudwatch_client.filter_log_events(
                            log_group_name=criteria.log_group_name,
                            log_stream_names=target_streams,
                            start_time=int(criteria.start_time.timestamp() * 1000)
                            if criteria.start_time
                            else None,
                            end_time=int(criteria.end_time.timestamp() * 1000)
                            if criteria.end_time
                            else None,
                            filter_pattern=criteria.filter_pattern,
                            next_token=next_token,
                            timeout=60.0,
                        ),
                        timeout=60.0,
                    )
                except TimeoutError:
                    logger.warning("CloudWatch API call timed out")
                    errors.append("API call timed out")
                    break
                except Exception as e:
                    logger.error(f"CloudWatch API call failed: {e}")
                    errors.append(f"API call failed: {str(e)}")
                    break

                api_calls_made += 1

                # Process events - CloudWatch has already filtered them
                raw_events = response.get("events", [])
                events_scanned += len(raw_events)

                logger.info(f"Received {len(raw_events)} pre-filtered events from CloudWatch")

                # Convert raw events to LogEvent objects
                for event_data in raw_events:
                    log_stream_name = event_data.get("logStreamName", "unknown")

                    # Simple conversion - no filtering needed, CloudWatch did it
                    timestamp = datetime.fromtimestamp(event_data["timestamp"] / 1000)
                    message = event_data.get("message", "")
                    event_id = event_data.get("eventId")
                    ingestion_time = None
                    if event_data.get("ingestionTime"):
                        ingestion_time = datetime.fromtimestamp(event_data["ingestionTime"] / 1000)

                    # Extract log level if present
                    log_level = self.pattern_matcher.extract_log_level(message)

                    # Parse metadata from JSON if applicable
                    metadata = {}
                    if message.strip().startswith("{"):
                        try:
                            import json

                            metadata = json.loads(message.strip())
                        except (json.JSONDecodeError, ValueError):
                            pass

                    from ..models.cloudwatch import LogEvent

                    event = LogEvent(
                        timestamp=timestamp,
                        message=message,
                        log_stream_name=log_stream_name,
                        log_level=log_level,
                        event_id=event_id,
                        ingestion_time=ingestion_time,
                        metadata=metadata,
                    )
                    all_events.append(event)
                    events_collected += 1

                    # Stop if we've collected enough events
                    if events_collected >= criteria.max_events:
                        break

                # Check if we should continue pagination
                # criteria.max_events
                if events_collected >= 1:
                    break

                next_token = response.get("nextToken")
                if not next_token:
                    break

            # Create final result
            return self._create_result(
                all_events,
                query_id,
                start_time,
                criteria,
                events_scanned,
                events_collected,
                api_calls_made,
                next_token,
                warnings,
                errors,
            )

        except Exception as e:
            end_time = datetime.now()
            execution_time_ms = (end_time - start_time).total_seconds() * 1000

            logger.error(f"Query {query_id} failed: {e}")

            # Return partial results with error
            return QueryResults(
                events=all_events,
                total_events=events_scanned,
                query_id=query_id,
                execution_time_ms=execution_time_ms,
                start_time=start_time,
                end_time=end_time,
                log_group_name=criteria.log_group_name,
                log_streams_queried=target_streams or [],
                events_scanned=events_scanned,
                events_matched=len(all_events),
                api_calls_made=api_calls_made,
                errors=[str(e)] + errors,
                warnings=warnings,
            )

    def _create_result(
        self,
        events,
        query_id,
        start_time,
        criteria,
        events_scanned,
        events_matched,
        api_calls_made,
        next_token,
        warnings,
        errors,
    ) -> QueryResults:
        """Create a QueryResults object."""
        end_time = datetime.now()
        execution_time_ms = (end_time - start_time).total_seconds() * 1000

        logger.info(
            f"Query {query_id} completed: {len(events)} events matched "
            f"from {events_scanned} scanned in {execution_time_ms:.0f}ms"
        )

        return QueryResults(
            events=events,
            total_events=events_scanned,
            query_id=query_id,
            execution_time_ms=execution_time_ms,
            start_time=start_time,
            end_time=end_time,
            next_token=next_token,
            has_more_events=bool(next_token),
            log_group_name=criteria.log_group_name,
            log_streams_queried=getattr(criteria, "target_streams", []),
            events_scanned=events_scanned,
            events_matched=events_matched,
            api_calls_made=api_calls_made,
            errors=errors,
            warnings=warnings,
        )

    def _create_empty_result(
        self, query_id, start_time, criteria, warnings, errors
    ) -> QueryResults:
        """Create an empty QueryResults object."""
        end_time = datetime.now()
        execution_time_ms = (end_time - start_time).total_seconds() * 1000

        return QueryResults(
            events=[],
            total_events=0,
            query_id=query_id,
            execution_time_ms=execution_time_ms,
            start_time=start_time,
            end_time=end_time,
            log_group_name=criteria.log_group_name,
            log_streams_queried=[],
            events_scanned=0,
            events_matched=0,
            api_calls_made=0,
            errors=errors,
            warnings=warnings,
        )

    async def _get_active_log_streams(self, log_group_name: str, limit: int = 10) -> list[str]:
        """
        Get list of active log streams from log group.

        Args:
            log_group_name: Name of the log group
            limit: Maximum number of streams to return (default 10 for speed)

        Returns:
            List of log stream names, sorted by most recent activity
        """
        try:
            # Get streams ordered by last event time with smaller limit for speed
            streams = await self.cloudwatch_client.describe_log_streams(
                log_group_name=log_group_name,
                order_by="LastEventTime",
                descending=True,
                limit=limit,  # Use parameter for flexibility
            )

            # Filter to streams with recent activity (within last 7 days)
            recent_threshold = datetime.now().timestamp() - (7 * 24 * 60 * 60)
            active_streams = []

            for stream in streams:
                if stream.last_event_time:
                    if stream.last_event_time.timestamp() > recent_threshold:
                        active_streams.append(stream.log_stream_name)
                else:
                    # Include streams without last_event_time (might be very new)
                    active_streams.append(stream.log_stream_name)

            logger.debug(f"Found {len(active_streams)} active streams in {log_group_name}")
            return active_streams

        except Exception as e:
            logger.warning(f"Failed to get active streams for {log_group_name}: {e}")
            return []

    def get_statistics(self) -> dict[str, Any]:
        """
        Get filtering statistics.

        Returns:
            Dictionary with pattern matching and processing statistics
        """
        return {
            "pattern_matcher": self.pattern_matcher.get_statistics(),
            "log_filter": {
                "service_status": "active",
                "client_initialized": self.cloudwatch_client.client is not None,
            },
        }

    async def close(self):
        """Close the log filter service and clean up resources."""
        await self.cloudwatch_client.close()
        self.pattern_matcher.reset_statistics()
        logger.debug("Log filter service closed")
