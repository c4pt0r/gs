"""
Configuration management for gmail
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class AuthConfig:
    """Authentication configuration"""

    credentials: Optional[str] = None
    auth_token: Optional[str] = None
    cached_auth_token: str = field(
        default_factory=lambda: os.path.expanduser("~/.gmail/tokens")
    )
    force_headless: bool = False
    ignore_token: bool = False


@dataclass
class FilterConfig:
    """Email filtering configuration"""

    query: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    from_email: Optional[str] = None
    to: Optional[str] = None
    subject: Optional[str] = None
    has_attachment: bool = False
    unread_only: bool = False
    since: Optional[str] = None


@dataclass
class CheckpointConfig:
    """Checkpoint configuration"""

    checkpoint_file: str = field(
        default_factory=lambda: os.path.expanduser("~/.gmail/checkpoint")
    )
    checkpoint_interval: int = 60
    resume: bool = False
    reset_checkpoint: bool = False


@dataclass
class OutputConfig:
    """Output format configuration"""

    format: str = "json"
    fields: Optional[List[str]] = None
    include_body: bool = False
    include_attachments: bool = False
    max_body_length: Optional[int] = None
    pretty: bool = False


@dataclass
class CacheConfig:
    """Cache configuration"""

    enabled: bool = True
    cache_file: str = field(
        default_factory=lambda: os.path.expanduser("~/.gmail/cache.db")
    )
    max_age_days: int = 30
    cleanup_interval: int = 86400  # 24 hours in seconds
    clear_cache: bool = False


@dataclass
class MonitoringConfig:
    """Monitoring behavior configuration"""

    poll_interval: int = 30
    batch_size: int = 10
    tail: bool = False
    once: bool = False
    max_messages: Optional[int] = None


@dataclass
class Config:
    """Main configuration class"""

    auth: AuthConfig = field(default_factory=AuthConfig)
    filters: FilterConfig = field(default_factory=FilterConfig)
    checkpoint: CheckpointConfig = field(default_factory=CheckpointConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)

    verbose: bool = False
    quiet: bool = False
    log_file: Optional[str] = None
    dry_run: bool = False

    @classmethod
    def from_file(cls, config_file: str) -> "Config":
        """Load configuration from YAML file"""
        with open(config_file, "r") as f:
            data = yaml.safe_load(f) or {}

        config = cls()

        # Load auth config
        if "auth" in data:
            auth_data = data["auth"]
            config.auth = AuthConfig(
                credentials=auth_data.get("credentials_file"),
                auth_token=auth_data.get("auth_token"),
                cached_auth_token=auth_data.get(
                    "cached_auth_token", config.auth.cached_auth_token
                ),
                force_headless=auth_data.get("force_headless", False),
                ignore_token=auth_data.get("ignore_token", False),
            )

        # Load filter config
        if "filters" in data:
            filter_data = data["filters"]
            config.filters = FilterConfig(
                query=filter_data.get("query"),
                labels=filter_data.get("labels", []),
                from_email=filter_data.get("from"),
                to=filter_data.get("to"),
                subject=filter_data.get("subject"),
                has_attachment=filter_data.get("has_attachment", False),
                unread_only=filter_data.get("unread_only", False),
                since=filter_data.get("since"),
            )

        # Load output config
        if "output" in data:
            output_data = data["output"]
            config.output = OutputConfig(
                format=output_data.get("format", "json"),
                fields=output_data.get("fields"),
                include_body=output_data.get("include_body", False),
                include_attachments=output_data.get("include_attachments", False),
                max_body_length=output_data.get("max_body_length"),
                pretty=output_data.get("pretty", False),
            )

        # Load monitoring config
        if "monitoring" in data:
            monitoring_data = data["monitoring"]
            config.monitoring = MonitoringConfig(
                poll_interval=monitoring_data.get("poll_interval", 30),
                batch_size=monitoring_data.get("batch_size", 10),
                tail=monitoring_data.get("tail", False),
                once=monitoring_data.get("once", False),
                max_messages=monitoring_data.get("max_messages"),
            )

        # Load checkpoint config
        if "checkpoint" in data:
            checkpoint_data = data["checkpoint"]
            config.checkpoint = CheckpointConfig(
                checkpoint_file=checkpoint_data.get(
                    "checkpoint_file", config.checkpoint.checkpoint_file
                ),
                checkpoint_interval=checkpoint_data.get("checkpoint_interval", 60),
                resume=checkpoint_data.get("resume", False),
                reset_checkpoint=checkpoint_data.get("reset_checkpoint", False),
            )

        # Load cache config
        if "cache" in data:
            cache_data = data["cache"]
            config.cache = CacheConfig(
                enabled=cache_data.get("enabled", False),
                cache_file=cache_data.get("cache_file", config.cache.cache_file),
                max_age_days=cache_data.get("max_age_days", 30),
                cleanup_interval=cache_data.get("cleanup_interval", 86400),
                clear_cache=cache_data.get("clear_cache", False),
            )

        # Load other options
        config.verbose = data.get("verbose", False)
        config.quiet = data.get("quiet", False)
        config.log_file = data.get("log_file")
        config.dry_run = data.get("dry_run", False)

        return config

    @classmethod
    def from_cli_args(cls, **kwargs) -> "Config":
        """Create configuration from CLI arguments"""
        # Load from config file if provided
        if kwargs.get("config_file"):
            config = cls.from_file(kwargs["config_file"])
        else:
            config = cls()

        # Override with CLI arguments
        if kwargs.get("credentials"):
            config.auth.credentials = kwargs["credentials"]
        if kwargs.get("auth_token"):
            config.auth.auth_token = kwargs["auth_token"]
        if kwargs.get("cached_auth_token"):
            config.auth.cached_auth_token = kwargs["cached_auth_token"]
        if kwargs.get("force_headless"):
            config.auth.force_headless = kwargs["force_headless"]
        if kwargs.get("ignore_token"):
            config.auth.ignore_token = kwargs["ignore_token"]

        # Filter options
        if kwargs.get("query"):
            config.filters.query = kwargs["query"]
        if kwargs.get("label"):
            config.filters.labels = list(kwargs["label"])
        if kwargs.get("from_email"):
            config.filters.from_email = kwargs["from_email"]
        if kwargs.get("to"):
            config.filters.to = kwargs["to"]
        if kwargs.get("subject"):
            config.filters.subject = kwargs["subject"]
        if kwargs.get("has_attachment"):
            config.filters.has_attachment = kwargs["has_attachment"]
        if kwargs.get("unread_only"):
            config.filters.unread_only = kwargs["unread_only"]
        if kwargs.get("since"):
            config.filters.since = kwargs["since"]

        # Checkpoint options
        if kwargs.get("checkpoint_file"):
            config.checkpoint.checkpoint_file = kwargs["checkpoint_file"]
        if kwargs.get("checkpoint_interval"):
            config.checkpoint.checkpoint_interval = kwargs["checkpoint_interval"]
        if kwargs.get("resume"):
            config.checkpoint.resume = kwargs["resume"]
        if kwargs.get("reset_checkpoint"):
            config.checkpoint.reset_checkpoint = kwargs["reset_checkpoint"]

        # Output options
        if kwargs.get("output_format"):
            config.output.format = kwargs["output_format"]
        if kwargs.get("fields"):
            config.output.fields = (
                kwargs["fields"].split(",") if kwargs["fields"] else None
            )
        if kwargs.get("include_body"):
            config.output.include_body = kwargs["include_body"]
        if kwargs.get("include_attachments"):
            config.output.include_attachments = kwargs["include_attachments"]
        if kwargs.get("max_body_length"):
            config.output.max_body_length = kwargs["max_body_length"]
        if kwargs.get("pretty"):
            config.output.pretty = kwargs["pretty"]

        # Monitoring options
        if kwargs.get("poll_interval"):
            config.monitoring.poll_interval = kwargs["poll_interval"]
        if kwargs.get("batch_size"):
            config.monitoring.batch_size = kwargs["batch_size"]
        if kwargs.get("tail"):
            config.monitoring.tail = kwargs["tail"]
        if kwargs.get("once"):
            config.monitoring.once = kwargs["once"]
        if kwargs.get("max_messages"):
            config.monitoring.max_messages = kwargs["max_messages"]

        # Cache options
        if kwargs.get("no_cache"):
            config.cache.enabled = False
        if kwargs.get("cache_file"):
            config.cache.cache_file = kwargs["cache_file"]
        if kwargs.get("cache_max_age_days"):
            config.cache.max_age_days = kwargs["cache_max_age_days"]
        if kwargs.get("clear_cache"):
            config.cache.clear_cache = kwargs["clear_cache"]

        # Other options
        if kwargs.get("verbose"):
            config.verbose = kwargs["verbose"]
        if kwargs.get("quiet"):
            config.quiet = kwargs["quiet"]
        if kwargs.get("log_file"):
            config.log_file = kwargs["log_file"]
        if kwargs.get("dry_run"):
            config.dry_run = kwargs["dry_run"]

        return config

    def ensure_directories(self):
        """Ensure necessary directories exist"""
        directories = [
            os.path.dirname(self.auth.cached_auth_token),
            os.path.dirname(self.checkpoint.checkpoint_file),
        ]

        if self.cache.enabled:
            directories.append(os.path.dirname(self.cache.cache_file))

        if self.log_file:
            directories.append(os.path.dirname(self.log_file))

        for directory in directories:
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
