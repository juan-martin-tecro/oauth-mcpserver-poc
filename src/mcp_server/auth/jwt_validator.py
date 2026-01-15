"""JWT Validation using PyJWT with JWKS from Auth0."""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import jwt
from jwt import PyJWKClient
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidTokenError,
)

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class JWTClaims:
    """Parsed JWT claims with standard and custom fields."""

    sub: str
    iss: str
    aud: List[str]
    exp: int
    iat: int
    scope: Optional[str] = None
    raw_claims: Dict[str, Any] = field(default_factory=dict)

    @property
    def scopes(self) -> List[str]:
        """Parse scope string into list."""
        return self.scope.split() if self.scope else []

    def get_custom_claim(self, claim_name: str) -> Optional[Any]:
        """Get custom claim from Ares namespace."""
        namespace = settings.jwt_custom_claims_namespace
        return self.raw_claims.get(f"{namespace}{claim_name}")

    @property
    def email(self) -> Optional[str]:
        """Get email from custom claims."""
        return self.get_custom_claim("email")

    @property
    def role(self) -> Optional[str]:
        """Get role from custom claims."""
        return self.get_custom_claim("role")

    @property
    def teams(self) -> Optional[Dict[str, Any]]:
        """Get teams from custom claims."""
        return self.get_custom_claim("teams")


class JWTValidator:
    """Validates JWTs using JWKS from Auth0."""

    def __init__(self):
        self._jwks_client = PyJWKClient(
            str(settings.jwt_jwks_url),
            cache_keys=True,
            lifespan=300,  # Cache JWKS for 5 minutes
        )

    def validate(self, token: str) -> JWTClaims:
        """
        Validate JWT and return claims.

        Args:
            token: The JWT string to validate

        Returns:
            JWTClaims: Parsed and validated claims

        Raises:
            InvalidTokenError: If token is invalid
            ExpiredSignatureError: If token has expired
            InvalidAudienceError: If audience doesn't match
        """
        try:
            # Get signing key from JWKS based on token's kid header
            signing_key = self._jwks_client.get_signing_key_from_jwt(token)

            # Decode and validate token
            # Note: audience validation in PyJWT checks if expected audience
            # is IN the token's aud claim (handles array aud correctly)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=settings.jwt_algorithms,
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
                options={
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "require": ["exp", "iss", "aud", "sub"],
                },
            )

            # Handle audience as array or string
            aud = payload.get("aud", [])
            if isinstance(aud, str):
                aud = [aud]

            return JWTClaims(
                sub=payload["sub"],
                iss=payload["iss"],
                aud=aud,
                exp=payload["exp"],
                iat=payload.get("iat", 0),
                scope=payload.get("scope"),
                raw_claims=payload,
            )

        except ExpiredSignatureError:
            logger.warning("Token has expired")
            raise
        except InvalidAudienceError:
            logger.warning("Invalid audience in token")
            raise
        except InvalidTokenError as e:
            logger.warning(f"Token validation failed: {e}")
            raise


# Singleton instance
jwt_validator = JWTValidator()
