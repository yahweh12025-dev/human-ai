#!/usr/bin/env python3
"""
Swarm Logger Utility
Provides standardized logging for all agents in the Human-AI Agent Swarm.
Outputs both human-readable and JSON lines for easy parsing.
"""

import json
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class LogLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class SwarmLogger:
    def __init__(self, source: str, output_stream=sys.stdout):
        """
        Initialize a SwarmLogger for a specific source (e.g., agent name).

        Args:
            source: Identifier for the source of logs (e.g., 'health_bot', 'navigator')
            output_stream: Where to write logs (default: stdout)
        """
        self.source = source
        self.output_stream = output_stream

    def _log(self, level: LogLevel, message: str, **kwargs):
        """Internal method to log a message with optional structured data."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "source": self.source,
            "level": level.value,
            "message": message,
        }
        # Add any extra fields provided
        if kwargs:
            log_entry["data"] = kwargs

        # Output as JSON line for machine parsing
        json_line = json.dumps(log_entry)
        # Also output a human-readable version
        human_line = f"[{log_entry['timestamp']}] {level.value:8} [{self.source}] {message}"
        if kwargs:
            human_line += f" | {kwargs}"

        # Write both versions (separated by a delimiter or on separate lines?)
        # We'll write the JSON line first, then the human line on the next line for simplicity.
        # However, for backward compatibility with existing log parsing, we might want just one line.
        # Let's output only the JSON line for now, as it contains all information and is parsable.
        # If human readability is needed, a log viewer can pretty-print the JSON.
        self.output_stream.write(json_line + "\n")
        self.output_stream.flush()

    def info(self, message: str, **kwargs):
        self._log(LogLevel.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(LogLevel.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(LogLevel.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(LogLevel.CRITICAL, message, **kwargs)


# Convenience function to get a logger for a module
def get_logger(source: str) -> SwarmLogger:
    """Get a SwarmLogger instance for the given source."""
    return SwarmLogger(source)


if __name__ == "__main__":
    # Example usage
    logger = SwarmLogger("test_logger")
    logger.info("This is an informational message", task_id="test-123")
    logger.warning("This is a warning", retry_count=3)
    logger.error("This is an error", error_code=500, details="Something broke")
    logger.critical("This is critical", requires_immediate_attention=True)