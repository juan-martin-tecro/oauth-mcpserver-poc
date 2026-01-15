"""PKCE (Proof Key for Code Exchange) utilities for OAuth 2.1."""

import base64
import hashlib
import secrets
from typing import Tuple


def generate_pkce_pair() -> Tuple[str, str]:
    """
    Generate PKCE code_verifier and code_challenge using S256.

    Per RFC 7636, the code_verifier is a cryptographically random string
    using unreserved characters [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~",
    with a minimum length of 43 characters and maximum of 128 characters.

    The code_challenge is the Base64url-encoded SHA256 hash of the code_verifier.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate random code_verifier (43-128 chars, using 64 for good entropy)
    code_verifier = secrets.token_urlsafe(64)[:128]

    # Generate code_challenge using S256
    # SHA256 hash, then Base64url encode without padding
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return code_verifier, code_challenge


def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """
    Verify that a code_verifier matches a code_challenge.

    Args:
        code_verifier: The original code verifier
        code_challenge: The challenge to verify against

    Returns:
        True if the verifier produces the same challenge, False otherwise
    """
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return secrets.compare_digest(computed_challenge, code_challenge)
