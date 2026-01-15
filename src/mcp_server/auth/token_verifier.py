"""Token verifier implementation for MCP SDK integration."""

import logging
from typing import Optional

from jwt.exceptions import InvalidTokenError

from .jwt_validator import JWTClaims, jwt_validator

logger = logging.getLogger(__name__)


class AccessTokenInfo:
    """Information about a validated access token."""

    def __init__(
        self,
        token: str,
        client_id: str,
        scopes: list[str],
        expires_at: int,
        claims: JWTClaims,
    ):
        self.token = token
        self.client_id = client_id
        self.scopes = scopes
        self.expires_at = expires_at
        self.claims = claims

    @property
    def email(self) -> Optional[str]:
        """Get email from claims."""
        return self.claims.email

    @property
    def role(self) -> Optional[str]:
        """Get role from claims."""
        return self.claims.role


class Auth0TokenVerifier:
    """
    Token verifier that validates JWTs issued by Auth0.

    This class provides token verification for the MCP server,
    validating JWT signatures, expiration, issuer, and audience.
    """

    async def verify_token(self, token: str) -> Optional[AccessTokenInfo]:
        """
        Verify a bearer token and return AccessTokenInfo if valid.

        Args:
            token: The bearer token (JWT) to verify

        Returns:
            AccessTokenInfo if valid, None if invalid
        """
        try:
            claims: JWTClaims = jwt_validator.validate(token)

            return AccessTokenInfo(
                token=token,
                client_id=claims.sub,
                scopes=claims.scopes,
                expires_at=claims.exp,
                claims=claims,
            )

        except InvalidTokenError as e:
            logger.debug(f"Token verification failed: {e}")
            return None

    def verify_token_sync(self, token: str) -> Optional[AccessTokenInfo]:
        """
        Synchronous version of verify_token.

        Args:
            token: The bearer token (JWT) to verify

        Returns:
            AccessTokenInfo if valid, None if invalid
        """
        try:
            claims: JWTClaims = jwt_validator.validate(token)

            return AccessTokenInfo(
                token=token,
                client_id=claims.sub,
                scopes=claims.scopes,
                expires_at=claims.exp,
                claims=claims,
            )

        except InvalidTokenError as e:
            logger.debug(f"Token verification failed: {e}")
            return None
