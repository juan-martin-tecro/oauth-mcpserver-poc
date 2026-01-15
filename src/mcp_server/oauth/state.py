"""OAuth state management for PKCE flow."""

import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class OAuthStateStore:
    """
    Thread-safe in-memory store for OAuth state parameters.

    States expire after a configurable TTL (default 10 minutes).
    States are single-use and deleted after retrieval.
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

    def get(self, state: str) -> Optional[Dict[str, Any]]:
        """
        Get and delete state data if not expired (single-use).

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
