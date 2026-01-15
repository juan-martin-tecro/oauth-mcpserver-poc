"""OAuth state management for PKCE flow."""

import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class OAuthStateStore:
    """
    Thread-safe in-memory store for OAuth state parameters.

    States expire after a configurable TTL (default 10 minutes).
    States are single-use and deleted after successful token exchange
    to allow retries on errors while maintaining security.
    """

    def __init__(self, ttl_minutes: int = 10):
        """
        Initialize the state store.

        Args:
            ttl_minutes: Time-to-live for states in minutes
        """
        self._store: Dict[str, tuple[datetime, Dict[str, Any]]] = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = threading.Lock()

    def save(self, state: str, data: Dict[str, Any]) -> None:
        """
        Save state data with timestamp.

        Args:
            state: The state parameter (unique identifier)
            data: Data to associate with the state
        """
        with self._lock:
            self._cleanup()
            self._store[state] = (datetime.utcnow(), data)

    def peek(self, state: str) -> Optional[Dict[str, Any]]:
        """
        Get state data without consuming it (for validation/retry scenarios).

        This allows the callback to be called multiple times (e.g., browser prefetch,
        retries on errors) while still maintaining security by consuming the state
        only after successful token exchange.

        Args:
            state: The state parameter to look up

        Returns:
            The associated data if found and not expired, None otherwise
        """
        with self._lock:
            self._cleanup()
            if state in self._store:
                timestamp, data = self._store[state]
                if datetime.utcnow() - timestamp < self._ttl:
                    return data
        return None

    def consume(self, state: str) -> bool:
        """
        Explicitly consume (delete) a state after successful token exchange.

        This should only be called after a successful token exchange to prevent
        replay attacks while allowing retries on errors.

        Args:
            state: The state parameter to consume

        Returns:
            True if the state was found and consumed, False otherwise
        """
        with self._lock:
            if state in self._store:
                del self._store[state]
                return True
        return False

    def get(self, state: str) -> Optional[Dict[str, Any]]:
        """
        Get and delete state data if not expired (single-use).

        DEPRECATED: Use peek() + consume() instead for better error handling.
        This method is kept for backward compatibility but should be avoided
        in new code as it doesn't allow retries on errors.

        Args:
            state: The state parameter to look up

        Returns:
            The associated data if found and not expired, None otherwise
        """
        with self._lock:
            self._cleanup()
            if state in self._store:
                timestamp, data = self._store.pop(state)
                if datetime.utcnow() - timestamp < self._ttl:
                    return data
        return None

    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = datetime.utcnow()
        expired = [
            key
            for key, (timestamp, _) in self._store.items()
            if now - timestamp >= self._ttl
        ]
        for key in expired:
            del self._store[key]


# Singleton instance
oauth_state_store = OAuthStateStore()
