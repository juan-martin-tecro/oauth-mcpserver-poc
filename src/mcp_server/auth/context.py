"""Context variables for passing auth info to MCP tools."""

from contextvars import ContextVar
from typing import Optional

# ContextVar to store the bearer token for the current request
# This allows MCP tools to access the token without direct access to the Starlette request
current_bearer_token: ContextVar[Optional[str]] = ContextVar(
    "current_bearer_token", default=None
)


def get_current_token() -> Optional[str]:
    """Get the bearer token for the current request context."""
    return current_bearer_token.get()


def set_current_token(token: str) -> None:
    """Set the bearer token for the current request context."""
    current_bearer_token.set(token)


def clear_current_token() -> None:
    """Clear the bearer token for the current request context."""
    current_bearer_token.set(None)
