"""Authentication module for MCP Server."""

from .jwt_validator import JWTValidator, JWTClaims, jwt_validator
from .token_verifier import Auth0TokenVerifier
from .protected_resource import (
    get_protected_resource_metadata,
    get_www_authenticate_header,
    get_protected_resource_routes,
)
from .middleware import BearerAuthMiddleware

__all__ = [
    "JWTValidator",
    "JWTClaims",
    "jwt_validator",
    "Auth0TokenVerifier",
    "get_protected_resource_metadata",
    "get_www_authenticate_header",
    "get_protected_resource_routes",
    "BearerAuthMiddleware",
]
