"""Bearer authentication middleware for protected routes."""

import logging
from typing import Callable, List, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from ..config import settings
from .context import set_current_token, clear_current_token
from .protected_resource import get_www_authenticate_header
from .token_verifier import Auth0TokenVerifier

logger = logging.getLogger(__name__)


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces Bearer token authentication on protected routes.

    Returns 401 with WWW-Authenticate header per RFC 9728 when:
    - No Authorization header present
    - Invalid token format
    - Token validation fails
    """

    def __init__(
        self,
        app,
        token_verifier: Auth0TokenVerifier = None,
        excluded_paths: List[str] = None,
    ):
        super().__init__(app)
        self.token_verifier = token_verifier or Auth0TokenVerifier()
        self.excluded_paths = excluded_paths or [
            "/.well-known/oauth-protected-resource",
            "/healthz",
            "/auth/start",
            "/auth/callback",
            "/auth/refresh",
            "/docs",
            "/openapi.json",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and enforce authentication on protected routes."""
        # Skip auth for excluded paths
        if self._is_excluded(request.url.path):
            return await call_next(request)

        # Extract bearer token
        auth_header = request.headers.get("Authorization", "")
        token = self._extract_bearer_token(auth_header)

        if not token:
            logger.debug(f"No bearer token for path: {request.url.path}")
            return self._unauthorized_response("No valid bearer token provided")

        # Validate token
        access_token = await self.token_verifier.verify_token(token)

        if not access_token:
            logger.debug(f"Invalid token for path: {request.url.path}")
            return self._unauthorized_response("Invalid or expired token")

        # Store validated token info in request state for downstream use
        request.state.access_token = access_token
        request.state.bearer_token = token  # Raw token for forwarding

        # Also store in contextvar so MCP tools can access it
        # This is necessary because FastMCP tools don't have direct access to Starlette request
        set_current_token(token)

        try:
            return await call_next(request)
        finally:
            # Clear the token after the request is done
            clear_current_token()

    def _is_excluded(self, path: str) -> bool:
        """Check if path should skip authentication."""
        # Exact match or prefix match
        for excluded in self.excluded_paths:
            if path == excluded or path.startswith(excluded + "/"):
                return True
        return False

    def _extract_bearer_token(self, auth_header: str) -> Optional[str]:
        """Extract token from 'Bearer <token>' header."""
        if not auth_header.startswith("Bearer "):
            return None
        return auth_header[7:].strip()

    def _unauthorized_response(self, detail: str) -> JSONResponse:
        """
        Generate 401 response with WWW-Authenticate header per RFC 9728.
        """
        scope_str = " ".join(settings.supported_scopes)
        return JSONResponse(
            status_code=401,
            content={
                "error": "unauthorized",
                "error_description": detail,
            },
            headers={
                "WWW-Authenticate": get_www_authenticate_header(scope=scope_str),
            },
        )
