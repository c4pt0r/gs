"""
Interactive REPL mode for gmail
"""

import cmd
import shlex
import sys
from typing import List, Optional, Dict, Any

from .config import Config
from .client import GmailClient
from .formatter import OutputFormatter
from .checkpoint import Checkpoint


class GmailREPL(cmd.Cmd):
    """Interactive REPL for gmail"""

    intro = "Welcome to gmail REPL mode. Type 'help' for commands."

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.client = GmailClient(config)
        self.formatter = OutputFormatter(config)
        self.checkpoint = None
        self.current_label = "INBOX"

        # Override output format for REPL to be human-readable
        self.config.output.format = "compact"

        # Set initial prompt
        self.prompt = f"gmail({self.current_label})> "

    def run(self):
        """Start the REPL"""
        try:
            # Ensure directories exist
            self.config.ensure_directories()

            # Connect to Gmail
            print("Connecting to Gmail API...")
            self.client.connect()
            print("Connected successfully")

            # Initialize checkpoint
            self.checkpoint = Checkpoint(self.config)

            # Start command loop
            self.cmdloop()

        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    def do_query(self, args: str):
        """Execute a Gmail query
        Usage: query <query-string>
        Example: query from:noreply@github.com subject:alert
        """
        if not args.strip():
            print("Error: Query string is required")
            return

        try:
            # Execute query
            result = self.client.list_messages(
                query=args.strip(), max_results=self.config.monitoring.batch_size
            )

            messages = result.get("messages", [])
            if messages:
                print(f"\n=== Found {len(messages)} messages ===")
                print()

                # Process and display messages
                for i, message_info in enumerate(messages, 1):
                    parsed_message = self.client.get_parsed_message(message_info["id"])
                    if parsed_message:
                        print(f"{i:2d}. [{message_info['id']}] ", end="")
                        self.formatter.output_message(parsed_message)
                print()
            else:
                print("No messages found for this query")

        except Exception as e:
            print(f"Error executing query: {e}")

    def do_tail(self, args: str):
        """Tail emails from a mailbox or label
        Usage: tail [mailbox/label] [num_of_emails]
        Example: tail INBOX 10
        Example: tail important 5
        """
        parts = shlex.split(args) if args else []

        # Parse arguments
        label = self.current_label
        num_emails = 10

        if len(parts) >= 1:
            label = parts[0]
        if len(parts) >= 2:
            try:
                num_emails = int(parts[1])
            except ValueError:
                print("Error: Number of emails must be an integer")
                return

        try:
            # Build query for the label
            query = f"in:{label}"

            # Get messages
            result = self.client.list_messages(query=query, max_results=num_emails)

            messages = result.get("messages", [])
            if messages:
                print(f"\n=== Showing {len(messages)} recent emails from {label} ===")
                print()

                # Process and display messages
                for i, message_info in enumerate(messages, 1):
                    parsed_message = self.client.get_parsed_message(message_info["id"])
                    if parsed_message:
                        print(f"{i:2d}. [{message_info['id']}] ", end="")
                        self.formatter.output_message(parsed_message)
                print()
            else:
                print(f"No emails found in {label}")

        except Exception as e:
            print(f"Error tailing {label}: {e}")

    def do_ls(self, args: str):
        """List emails from current or specified label

        Usage:
            ls [--unread|-u] [LABEL] [LIMIT]

        Arguments:
            LABEL   Label/mailbox name (default: current label)
            LIMIT   Number of emails to show (default: 10)

        Options:
            --unread, -u    Show only unread emails

        Examples:
            ls                    # Show 10 emails from current label
            ls 20                 # Show 20 emails from current label
            ls INBOX              # Show 10 emails from INBOX
            ls INBOX 20           # Show 20 emails from INBOX
            ls --unread           # Show unread emails from current label
            ls --unread INBOX 20  # Show 20 unread emails from INBOX

        Note: For numeric label names, use quotes: ls "123"
        """
        parts = shlex.split(args) if args else []

        # Parse options first
        unread_mode = False
        filtered_parts = []

        i = 0
        while i < len(parts):
            if parts[i] in ["--unread", "-u"]:
                unread_mode = True
            elif parts[i] == "unread":  # Keep backward compatibility
                unread_mode = True
            else:
                filtered_parts.append(parts[i])
            i += 1

        # Parse remaining arguments: [label] [limit]
        label = self.current_label
        limit = 10

        # Parse arguments based on their types and positions
        if len(filtered_parts) == 1:
            arg = filtered_parts[0]
            if arg.isdigit():
                # Single numeric argument - treat as limit
                limit = int(arg)
            else:
                # Single non-numeric argument - treat as label
                label = arg
        elif len(filtered_parts) == 2:
            # Two arguments - determine which is label and which is limit
            first, second = filtered_parts[0], filtered_parts[1]

            if first.isdigit() and second.isdigit():
                # Both are numeric - this is ambiguous, treat first as limit
                print(
                    "Warning: Both arguments are numeric. Treating first as limit, second as label."
                )
                limit = int(first)
                label = second
            elif first.isdigit() and not second.isdigit():
                # First is numeric, second is not - first is limit, second is label
                limit = int(first)
                label = second
            elif not first.isdigit() and second.isdigit():
                # First is not numeric, second is - first is label, second is limit
                label = first
                limit = int(second)
            else:
                # Neither is numeric - first is label, second is invalid
                label = first
                print(f"Warning: Ignoring non-numeric limit argument: {second}")
        elif len(filtered_parts) > 2:
            print("Error: Too many arguments. Usage: ls [--unread] [label] [limit]")
            return

        # Execute the appropriate command
        if unread_mode:
            # Call unread command with proper arguments
            unread_args = []
            if label != self.current_label:
                unread_args.append(label)
            if limit != self.config.monitoring.batch_size:
                unread_args.append(str(limit))
            return self.do_unread(" ".join(unread_args))
        else:
            # Call tail command with proper arguments
            tail_args = []
            if label != self.current_label:
                tail_args.append(label)
            if limit != 10:
                tail_args.append(str(limit))
            return self.do_tail(" ".join(tail_args))

    def do_unread(self, args: str):
        """Show unread emails from a label
        Usage: unread [label] [limit]
        Example: unread
        Example: unread important
        Example: unread INBOX 5
        """
        parts = shlex.split(args) if args else []

        # Parse arguments
        label = self.current_label
        limit = self.config.monitoring.batch_size

        if len(parts) >= 1:
            # If first argument is a number, treat it as limit for current label
            try:
                limit = int(parts[0])
            except ValueError:
                # If not a number, treat as label name
                label = parts[0]
        if len(parts) >= 2:
            try:
                limit = int(parts[1])
            except ValueError:
                print("Error: Limit must be an integer")
                return

        try:
            # Build query for unread emails in the label
            query = f"in:{label} is:unread"

            # Get messages
            result = self.client.list_messages(query=query, max_results=limit)

            messages = result.get("messages", [])
            if messages:
                print(f"\n=== Found {len(messages)} unread emails in {label} ===")
                print()

                # Process and display messages
                for i, message_info in enumerate(messages, 1):
                    parsed_message = self.client.get_parsed_message(message_info["id"])
                    if parsed_message:
                        print(f"{i:2d}. [{message_info['id']}] ", end="")
                        self.formatter.output_message(parsed_message)
                print()
            else:
                print(f"No unread emails found in {label}")

        except Exception as e:
            print(f"Error getting unread emails from {label}: {e}")

    def do_labels(self, args: str):
        """List all available labels
        Usage: labels
        """
        try:
            labels = self.client.service.users().labels().list(userId="me").execute()

            print("Available labels:")
            for label in labels.get("labels", []):
                label_name = label["name"]
                label_id = label["id"]
                print(f"  {label_name} ({label_id})")

        except Exception as e:
            print(f"Error getting labels: {e}")

    def do_profile(self, args: str):
        """Show Gmail profile information
        Usage: profile
        """
        try:
            profile = self.client.get_profile()
            if profile:
                print(f"Email: {profile.get('emailAddress', 'N/A')}")
                print(f"Messages Total: {profile.get('messagesTotal', 'N/A')}")
                print(f"Threads Total: {profile.get('threadsTotal', 'N/A')}")
                print(f"History ID: {profile.get('historyId', 'N/A')}")
            else:
                print("Could not retrieve profile information")

        except Exception as e:
            print(f"Error getting profile: {e}")

    def do_read(self, args: str):
        """Read a specific email by ID
        Usage: read <message-id> [without-body]
        Example: read 18c5b2a4f2e1d8f0
        Example: read 18c5b2a4f2e1d8f0 without-body
        """
        if not args.strip():
            print("Error: Message ID is required")
            return

        parts = shlex.split(args)
        message_id = parts[0]
        without_body = len(parts) > 1 and parts[1] == "without-body"

        try:
            # Always enable body and attachments for detailed view in REPL
            original_include_body = self.config.output.include_body
            original_include_attachments = self.config.output.include_attachments
            original_max_body_length = self.config.output.max_body_length
            self.config.output.include_body = True
            self.config.output.include_attachments = True
            # Set very high limit to avoid truncation in read command
            self.config.output.max_body_length = 10000000  # 10MB limit

            # Get the parsed message
            parsed_message = self.client.get_parsed_message(message_id)

            # Restore original settings
            self.config.output.include_body = original_include_body
            self.config.output.include_attachments = original_include_attachments
            self.config.output.max_body_length = original_max_body_length

            if not parsed_message:
                print(f"Message with ID '{message_id}' not found")
                return

            # Display the full message with more details
            print(f"\n=== Email Details ===")
            print(f"ID: {parsed_message.get('id', 'N/A')}")
            print(f"Subject: {parsed_message.get('subject', 'No subject')}")
            print(f"From: {self._format_email_address(parsed_message.get('from', {}))}")

            # Display recipients
            to_addresses = parsed_message.get("to", [])
            if to_addresses:
                print(
                    f"To: {', '.join([self._format_email_address(addr) for addr in to_addresses])}"
                )

            cc_addresses = parsed_message.get("cc", [])
            if cc_addresses:
                print(
                    f"CC: {', '.join([self._format_email_address(addr) for addr in cc_addresses])}"
                )

            print(f"Date: {parsed_message.get('date', 'N/A')}")
            print(f"Labels: {', '.join(parsed_message.get('labels', []))}")

            # Display attachments if any
            attachments = parsed_message.get("attachments", [])
            if attachments:
                print(f"Attachments: {len(attachments)} file(s)")
                for attachment in attachments:
                    filename = attachment.get("filename", "Unknown")
                    size = attachment.get("size", 0)
                    print(f"  - {filename} ({size} bytes)")

            # Display snippet
            snippet = parsed_message.get("snippet", "")
            if snippet:
                print(f"\nSnippet: {snippet}")

            # Display body if available and not in without-body mode
            if not without_body:
                body = parsed_message.get("body", "")
                if body:
                    # Check if body contains HTML and convert to readable text
                    readable_body = self._convert_html_to_text(body)
                    print(f"\n=== Body ===")
                    print(readable_body)
                elif not snippet:
                    print("\nNo body content available")

        except Exception as e:
            print(f"Error reading message {message_id}: {e}")

    def _convert_html_to_text(self, body: str) -> str:
        """Convert HTML body to human-readable text for REPL display"""
        # Check if the body contains HTML tags
        if "<" in body and ">" in body:
            try:
                import html2text

                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                h.ignore_emphasis = False
                h.body_width = 80  # Set reasonable width for terminal
                h.unicode_snob = True
                h.skip_internal_links = True
                return h.handle(body)
            except ImportError:
                # Fallback to basic HTML stripping if html2text is not available
                import html
                import re

                return html.unescape(re.sub(r"<[^>]+>", "", body))
        else:
            # Plain text, return as-is
            return body

    def _format_email_address(self, addr):
        """Format email address for display"""
        if isinstance(addr, dict):
            name = addr.get("name", "")
            email = addr.get("email", "")
            if name:
                return f"{name} <{email}>"
            else:
                return email
        return str(addr)

    def do_use(self, args: str):
        """Switch current label
        Usage: use <label>
        Example: use INBOX
        Example: use important
        """
        if not args.strip():
            print("Error: Label name is required")
            return

        label = args.strip()
        self.current_label = label
        self.prompt = f"gmail({self.current_label})> "
        print(f"Switched to label: {label}")

    def do_config(self, args: str):
        """Show current configuration
        Usage: config
        """
        print("Current configuration:")
        print(f"  Current label: {self.current_label}")
        print(f"  Batch size: {self.config.monitoring.batch_size}")
        print(f"  Poll interval: {self.config.monitoring.poll_interval}")
        print(f"  Output format: {self.config.output.format}")
        print(f"  Include body: {self.config.output.include_body}")
        print(f"  Include attachments: {self.config.output.include_attachments}")

        if self.config.filters.query:
            print(f"  Query filter: {self.config.filters.query}")
        if self.config.filters.from_email:
            print(f"  From filter: {self.config.filters.from_email}")
        if self.config.filters.to:
            print(f"  To filter: {self.config.filters.to}")
        if self.config.filters.subject:
            print(f"  Subject filter: {self.config.filters.subject}")
        if self.config.filters.labels:
            print(f"  Label filters: {', '.join(self.config.filters.labels)}")

    def do_exit(self, args: str):
        """Exit the REPL
        Usage: exit
        """
        print("Goodbye!")
        return True

    def do_quit(self, args: str):
        """Exit the REPL
        Usage: quit
        """
        return self.do_exit(args)

    def do_EOF(self, args: str):
        """Handle Ctrl+D"""
        print()
        return self.do_exit(args)

    def emptyline(self):
        """Handle empty line input"""
        pass

    def default(self, line: str):
        """Handle unknown commands"""
        print(f"Unknown command: {line}")
        print("Type 'help' for available commands")
