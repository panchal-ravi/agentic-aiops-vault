"""
CloudWatch Logs client for AWS integration.

This module provides the CloudWatch Logs client with authentication handling,
connection management, and retry logic for robust AWS API interactions.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

import boto3
import botocore.exceptions
from botocore.config import Config

from ..models.cloudwatch import CloudWatchCredentials, LogStreamInfo


logger = logging.getLogger(__name__)


class CloudWatchClient:
    """
    AWS CloudWatch Logs client with authentication and retry logic.

    Handles AWS authentication, regional configuration, and provides
    robust API interaction with exponential backoff retry.
    """

    def __init__(self, credentials: CloudWatchCredentials | None = None):
        """
        Initialize CloudWatch client with credentials.

        Args:
            credentials: AWS credentials. If None, uses default credential chain.
        """
        self.credentials = credentials or self._load_default_credentials()
        self.client = None
        self._session = None

        # Configure retry behavior with very short timeouts for responsiveness
        self.retry_config = Config(
            retries={"max_attempts": 1, "mode": "standard"},
            read_timeout=15,  # Reduced from 30 to 15 seconds
            connect_timeout=3,  # Reduced from 5 to 3 seconds
            max_pool_connections=5,
        )

    def _load_default_credentials(self) -> CloudWatchCredentials:
        """Load credentials from environment or default AWS configuration."""
        region = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1")

        return CloudWatchCredentials(
            region_name=region,
            access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            session_token=os.getenv("AWS_SESSION_TOKEN"),
            profile_name=os.getenv("AWS_PROFILE"),
        )

    async def _get_client(self):
        """Get or create CloudWatch Logs client with proper authentication."""
        if self.client is None:
            try:
                # Create session with credentials
                if self.credentials.profile_name:
                    session = boto3.Session(profile_name=self.credentials.profile_name)
                else:
                    session = boto3.Session(
                        aws_access_key_id=self.credentials.access_key_id,
                        aws_secret_access_key=self.credentials.secret_access_key,
                        aws_session_token=self.credentials.session_token,
                    )

                # Create CloudWatch Logs client
                self.client = session.client(
                    "logs", region_name=self.credentials.region_name, config=self.retry_config
                )

                # Test credentials with a simple API call
                await self._test_credentials()

                logger.info(
                    f"CloudWatch client initialized for region: {self.credentials.region_name}"
                )

            except Exception as e:
                logger.error(f"Failed to initialize CloudWatch client: {e}")
                raise

        return self.client

    async def _test_credentials(self):
        """Test AWS credentials with a simple API call."""
        try:
            # Use describe_log_groups with limit=1 as a lightweight test
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self.client.describe_log_groups(limit=1))
            logger.debug("CloudWatch credentials validated successfully")
        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code in ["InvalidUserID.NotFound", "AccessDenied", "UnauthorizedOperation"]:
                raise ValueError(f"AWS authentication failed: {error_code}")
            raise

    async def describe_log_groups(
        self, prefix: str | None = None, limit: int = 50, next_token: str | None = None
    ) -> dict[str, Any]:
        """
        Retrieve CloudWatch log groups.

        Args:
            prefix: Filter log groups by name prefix
            limit: Maximum number of log groups to return
            next_token: Pagination token for retrieving next page

        Returns:
            Raw AWS API response with logGroups and nextToken
        """
        client = await self._get_client()

        params = {"limit": min(limit, 50)}  # AWS API limit
        if prefix:
            params["logGroupNamePrefix"] = prefix
        if next_token:
            params["nextToken"] = next_token

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: client.describe_log_groups(**params)
            )

            logger.debug(f"Retrieved {len(response.get('logGroups', []))} log groups")
            return response

        except botocore.exceptions.ClientError as e:
            logger.error(f"Failed to describe log groups: {e}")
            raise

    async def describe_log_streams(
        self,
        log_group_name: str,
        prefix: str | None = None,
        order_by: str = "LastEventTime",
        descending: bool = True,
        limit: int = 50,
    ) -> list[LogStreamInfo]:
        """
        Retrieve log streams from a CloudWatch log group.

        Args:
            log_group_name: Name of the log group
            prefix: Filter streams by name prefix
            order_by: Sort order ('LogStreamName' or 'LastEventTime')
            descending: Sort in descending order
            limit: Maximum number of streams to return

        Returns:
            List of LogStreamInfo objects
        """
        client = await self._get_client()

        params = {
            "logGroupName": log_group_name,
            "orderBy": order_by,
            "descending": descending,
            "limit": min(limit, 50),  # AWS API limit
        }
        if prefix:
            params["logStreamNamePrefix"] = prefix

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, lambda: client.describe_log_streams(**params)
            )

            log_streams = []
            for stream in response.get("logStreams", []):
                log_streams.append(
                    LogStreamInfo(
                        log_stream_name=stream["logStreamName"],
                        log_group_name=log_group_name,
                        creation_time=datetime.fromtimestamp(stream["creationTime"] / 1000),
                        last_event_time=datetime.fromtimestamp(stream["lastEventTime"] / 1000)
                        if stream.get("lastEventTime")
                        else None,
                        last_ingestion_time=datetime.fromtimestamp(
                            stream["lastIngestionTime"] / 1000
                        )
                        if stream.get("lastIngestionTime")
                        else None,
                        upload_sequence_token=stream.get("uploadSequenceToken"),
                        arn=stream.get("arn"),
                        stored_bytes=stream.get("storedBytes"),
                    )
                )

            logger.debug(f"Retrieved {len(log_streams)} log streams from {log_group_name}")
            return log_streams

        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                raise ValueError(f"Log group not found: {log_group_name}")
            logger.error(f"Failed to describe log streams: {e}")
            raise

    async def filter_log_events(
        self,
        log_group_name: str,
        log_stream_names: list[str] | None = None,
        start_time: int | None = None,
        end_time: int | None = None,
        filter_pattern: str | None = None,
        next_token: str | None = None,
        timeout: float = 25.0,
    ) -> dict[str, Any]:
        """
        Filter log events from CloudWatch Logs using server-side filtering.

        Args:
            log_group_name: Name of the log group
            log_stream_names: List of specific log streams (None for all)
            start_time: Start time in Unix milliseconds
            end_time: End time in Unix milliseconds
            filter_pattern: CloudWatch filter pattern (server-side filtering)
            next_token: Pagination token
            timeout: Timeout for the API call

        Returns:
            Raw CloudWatch API response
        """
        client = await self._get_client()

        params = {
            "logGroupName": log_group_name,
            "interleaved": False,  # Don't interleave results from multiple streams
        }

        if log_stream_names:
            params["logStreamNames"] = log_stream_names
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        if filter_pattern:
            params["filterPattern"] = "{" + filter_pattern + "}"
        if next_token:
            params["nextToken"] = next_token

        try:
            loop = asyncio.get_event_loop()
            # Add timeout to prevent hanging on slow API calls
            # logger.info(f"Starting filter_log_events API call with params: {params}")
            response = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: client.filter_log_events(**params)),
                timeout=timeout,
            )

            logger.debug(f"Filtered {len(response.get('events', []))} events from {log_group_name}")
            return response

        except TimeoutError:
            logger.error(
                f"CloudWatch API call timed out after {timeout} seconds for {log_group_name}"
            )
            raise ValueError(f"CloudWatch API call timed out after {timeout} seconds")

        except botocore.exceptions.ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                raise ValueError(f"Log group not found: {log_group_name}")
            elif error_code == "InvalidParameterException":
                raise ValueError(f"Invalid filter parameters: {e.response['Error']['Message']}")
            elif error_code == "ThrottlingException":
                raise ValueError("AWS API rate limit exceeded")

            logger.error(f"Failed to filter log events: {e}")
            raise

    async def close(self):
        """Close the CloudWatch client and clean up resources."""
        if self.client:
            # Note: boto3 clients don't have explicit close methods
            # but we can clear the reference
            self.client = None
            logger.debug("CloudWatch client closed")
