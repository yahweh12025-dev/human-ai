#!/usr/bin/env python3
"""
BaseAgent: Unified abstract base for all human‑AI agents.

Features
-------
* Session initialization contract
* Structured logging via a class‑specific logger
* Exception handling wrapper for public methods
* Async/Sync resource cleanup hook

The goal is to provide a single place for common plumbing so future
agents can focus on their domain logic.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any

class BaseAgent(ABC):
    """Abstract base with a minimal lifecycle contract.

    Sub‑classes should call ``super().__init__`` to set up logging.
    """

    def __init__(self, name: str | None = None, log_level: int = logging.INFO):
        self.name = name or self.__class__.__name__
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(log_level)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '[%(asctime)s] %(name)s %(levelname)s: %(message)s',
                datefmt='%H:%M:%S',
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    @abstractmethod
    def initialize_session(self, *args: Any, **kwargs: Any) -> None:
        """Create any resources needed for an interaction.

        Concrete agents may read config files, start browsers, connect to
        LLMs, etc.
        """

    @abstractmethod
    async def close(self) -> None:
        """Cleanup resources.

        Agents that hold async resources (e.g., browsers) should close
        them here.
        """

    # ------------------------------------------------------------------
    # Utility wrappers
    # ------------------------------------------------------------------
    def _safe_call(self, func, *args, **kwargs):
        """Run *func* catching and logging exceptions.

        Used by agents to wrap public methods.
        """
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover – defensive guard
            self.logger.exception("Error in %s: %s", func.__name__, exc)
            raise

    # Context‑manager helpers for sync agents
    def __enter__(self):  # pragma: no cover – simple forwarding
        if not self._initialized:
            self.initialize_session()
            self._initialized = True
        return self

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover – simple forwarding
        self.close()

# End of file
