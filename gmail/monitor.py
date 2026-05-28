"""
Streaming monitor backing the `gmail tail` command
"""

import time
import signal
import sys
from typing import Optional, List, Dict, Any

from .config import Config
from .client import GmailClient
from .checkpoint import Checkpoint
from .formatter import OutputFormatter


class Monitor:
    """Continuous Gmail monitor backing `gmail tail`"""

    def __init__(self, config: Config):
        self.config = config
        self.client = GmailClient(config)
        self.formatter = OutputFormatter(config)
        self.checkpoint = None
        self.running = True
        self.message_count = 0

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.formatter.output_info("Shutting down...")
        # TODO: safe exit
        sys.exit(0)

    def run(self):
        """Main run loop"""
        try:
            # Ensure directories exist
            self.config.ensure_directories()

            # Connect to Gmail
            self.formatter.output_verbose("Connecting to Gmail API...")
            self.client.connect()
            self.formatter.output_verbose("Connected successfully")

            # Initialize checkpoint
            with Checkpoint(self.config) as checkpoint:
                self.checkpoint = checkpoint

                # Build query
                query = self.client.build_query()
                self.formatter.output_verbose(f"Using query: {query}")

                if self.config.dry_run:
                    self.formatter.output_info(
                        "Dry run mode - no emails will be processed"
                    )
                    return

                # Run monitoring
                if self.config.monitoring.once:
                    self._run_once(query)
                elif self.config.monitoring.tail:
                    self._run_follow(query)
                else:
                    self._run_once(query)

        except Exception as e:
            self.formatter.output_error(str(e))
            raise

    def _run_once(self, query: str):
        """Run once and exit"""
        self.formatter.output_verbose("Running in single-shot mode")

        try:
            # When --query is specified, fetch all results unless --max-messages is set
            if self.config.filters.query and not self.config.monitoring.max_messages:
                self.formatter.output_verbose("Fetching all messages matching query")
                messages = self._fetch_all_messages(query)

                # Process all fetched messages
                for message_info in messages:
                    if not self.running:
                        break

                    if (
                        self.config.monitoring.max_messages
                        and self.message_count >= self.config.monitoring.max_messages
                    ):
                        break

                    self._process_message(message_info["id"])
            else:
                # Use batch size for normal operation, loop until max_messages or no more results
                page_token = None

                while self.running:
                    # Fetch a batch of messages
                    result = self.client.list_messages(
                        query=query,
                        max_results=self.config.monitoring.batch_size,
                        page_token=page_token,
                    )
                    messages = result.get("messages", [])

                    if not messages:
                        self.formatter.output_verbose("No more messages to fetch")
                        break

                    self.formatter.output_verbose(
                        f"Fetched {len(messages)} messages in this batch"
                    )

                    # Process messages in this batch
                    for message_info in messages:
                        if not self.running:
                            break

                        if (
                            self.config.monitoring.max_messages
                            and self.message_count
                            >= self.config.monitoring.max_messages
                        ):
                            self.formatter.output_verbose(
                                f"Reached maximum message limit: {self.config.monitoring.max_messages}"
                            )
                            break

                        self._process_message(message_info["id"])

                    # Check if we should continue
                    if (
                        self.config.monitoring.max_messages
                        and self.message_count >= self.config.monitoring.max_messages
                    ):
                        break

                    # Check for next page
                    page_token = result.get("nextPageToken")
                    if not page_token:
                        self.formatter.output_verbose("No more pages to fetch")
                        break

            self.formatter.output_verbose(f"Processed {self.message_count} messages")

        except Exception as e:
            self.formatter.output_error(f"Error in single-shot mode: {e}")
            raise

    def _run_follow(self, query: str):
        """Run in follow mode (continuous monitoring)"""
        self.formatter.output_verbose("Running in follow mode")

        try:
            last_history_id = self.checkpoint.get_last_history_id()
            processed_count = 0

            while self.running:
                try:
                    if last_history_id:
                        # Use history API for incremental updates
                        history = self.client.get_history(
                            last_history_id,
                            max_results=self.config.monitoring.batch_size,
                        )

                        new_messages = []
                        for history_item in history.get("history", []):
                            for message_added in history_item.get("messagesAdded", []):
                                new_messages.append(message_added["message"]["id"])

                        if new_messages:
                            self.formatter.output_verbose(
                                f"Found {len(new_messages)} new messages from history"
                            )

                        # Process new messages
                        for message_id in new_messages:
                            if not self.running:
                                break

                            if (
                                self.config.monitoring.max_messages
                                and self.message_count
                                >= self.config.monitoring.max_messages
                            ):
                                self.formatter.output_verbose(
                                    "Reached maximum message limit"
                                )
                                self.running = False
                                break

                            self._process_message(message_id)

                        # Update history ID
                        if "historyId" in history:
                            last_history_id = history["historyId"]
                            self.checkpoint.update_history_id(last_history_id)

                    else:
                        # Initial fetch using list API
                        result = self.client.list_messages(
                            query=query, max_results=self.config.monitoring.batch_size
                        )

                        messages = result.get("messages", [])
                        if messages:
                            self.formatter.output_verbose(
                                f"Initial fetch: {len(messages)} messages"
                            )

                        # Process messages in reverse order (oldest first)
                        for message_info in reversed(messages):
                            if not self.running:
                                break

                            if (
                                self.config.monitoring.max_messages
                                and self.message_count
                                >= self.config.monitoring.max_messages
                            ):
                                self.formatter.output_verbose(
                                    "Reached maximum message limit"
                                )
                                self.running = False
                                break

                            self._process_message(message_info["id"])

                        # Get initial history ID from profile
                        profile = self.client.get_profile()
                        if profile and "historyId" in profile:
                            last_history_id = profile["historyId"]
                            self.checkpoint.update_history_id(last_history_id)

                    # Save checkpoint periodically
                    self.checkpoint.save()

                    # Clean up old message IDs
                    self.checkpoint.cleanup_old_message_ids()

                    # Sleep between polls
                    if self.running:
                        time.sleep(self.config.monitoring.poll_interval)

                    processed_count += 1

                except KeyboardInterrupt:
                    self.running = False
                    break
                except Exception as e:
                    self.formatter.output_error(f"Error in follow loop: {e}")
                    if self.running:
                        time.sleep(self.config.monitoring.poll_interval)

            self.formatter.output_verbose(
                f"Total processed: {self.message_count} messages"
            )

        except Exception as e:
            self.formatter.output_error(f"Error in follow mode: {e}")
            raise

    def _fetch_all_messages(self, query: str):
        """Fetch all messages matching the query using pagination"""
        all_messages = []
        page_token = None

        while True:
            result = self.client.list_messages(
                query=query,
                page_token=page_token,
                max_results=500,  # Use larger batch size for efficiency
            )

            messages = result.get("messages", [])
            all_messages.extend(messages)

            # Check if there are more pages
            page_token = result.get("nextPageToken")
            if not page_token:
                break

            self.formatter.output_verbose(
                f"Fetched {len(all_messages)} messages so far..."
            )

        return all_messages

    def _process_message(self, message_id: str) -> bool:
        """Process a single message"""
        try:
            # Check if already processed
            if self.checkpoint and self.checkpoint.is_message_processed(message_id):
                self.formatter.output_verbose(
                    f"Skipping already processed message: {message_id}"
                )
                return False

            # Fetch and parse message
            parsed_message = self.client.get_parsed_message(message_id)
            if not parsed_message:
                self.formatter.output_verbose(f"Could not fetch message: {message_id}")
                return False

            # Filter by subject pattern if specified
            if self.config.filters.subject and parsed_message.get("subject"):
                import re

                if not re.search(
                    self.config.filters.subject,
                    parsed_message["subject"],
                    re.IGNORECASE,
                ):
                    self.formatter.output_verbose(
                        f"Message filtered out by subject pattern: {message_id}"
                    )
                    return False

            # Output message
            self.formatter.output_message(parsed_message)

            # Update checkpoint
            if self.checkpoint:
                self.checkpoint.add_processed_message(message_id)
                if parsed_message.get("timestamp"):
                    self.checkpoint.update_timestamp(parsed_message["timestamp"])

            self.message_count += 1
            self.formatter.output_verbose(
                f"Processed message {self.message_count}: {message_id}"
            )

            return True

        except Exception as e:
            self.formatter.output_error(f"Error processing message {message_id}: {e}")
            return False
