"""Fallback OAuth endpoints for manual testing and clients without OAuth support."""

import logging
import secrets
import uuid
from typing import List
from urllib.parse import urlencode

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

from ..config import settings
from .pkce import generate_pkce_pair
from .state import oauth_state_store

logger = logging.getLogger(__name__)


async def auth_start(request: Request) -> RedirectResponse:
    """
    GET /auth/start - Initiates OAuth 2.1 authorization flow.

    Generates PKCE challenge and redirects to Ares authorization endpoint.
    The callback_url query param can override the default redirect URI.

    Query params:
        callback_url: Optional override for redirect URI
    """
    # Generate PKCE pair
    code_verifier, code_challenge = generate_pkce_pair()

    # Generate state parameter
    state = secrets.token_urlsafe(32)

    # Determine callback URL
    callback_url = request.query_params.get("callback_url", settings.oauth_redirect_uri)

    # Store state and code_verifier for callback
    oauth_state_store.save(
        state,
        {
            "code_verifier": code_verifier,
            "callback_url": callback_url,
        },
    )

    # Generate trace ID for Ares
    trace_id = str(uuid.uuid4())

    # Call Ares /authorize endpoint to get the redirect URL
    # Ares returns a JSON with redirect_url, not a direct redirect
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.auth_server_authorize_url,
                params={"callback_url": callback_url},
                headers={settings.trace_id_header: trace_id},
            )
            response.raise_for_status()
            data = response.json()
            auth_url = data.get("redirect_url")

            if not auth_url:
                return JSONResponse(
                    status_code=500,
                    content={"error": "server_error", "error_description": "No redirect_url from Ares"},
                )

            # Add state to the URL (Ares might not include it)
            # Parse and modify the URL to ensure state is included
            if "state=" not in auth_url:
                separator = "&" if "?" in auth_url else "?"
                auth_url = f"{auth_url}{separator}state={state}"

            return RedirectResponse(url=auth_url, status_code=302)

        except httpx.HTTPStatusError as e:
            logger.error(f"Ares authorize error: {e.response.text}")
            return JSONResponse(
                status_code=e.response.status_code,
                content={"error": "authorization_error", "error_description": str(e)},
            )
        except Exception as e:
            logger.error(f"Failed to initiate auth: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": "server_error", "error_description": str(e)},
            )


async def auth_callback(request: Request) -> JSONResponse:
    """
    GET /auth/callback - Handles OAuth callback with code exchange.

    Exchanges authorization code for tokens using PKCE via Ares.

    Query params:
        code: Authorization code from Auth0/Ares
        state: State parameter for CSRF protection
        error: Error code if authorization failed
        error_description: Error description
    """
    # Extract query parameters
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        return JSONResponse(
            status_code=400,
            content={
                "error": error,
                "error_description": request.query_params.get("error_description", ""),
            },
        )

    if not code or not state:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "Missing code or state parameter",
            },
        )

    # Retrieve stored state data without consuming it (allows retries on errors)
    state_data = oauth_state_store.peek(state)
    if not state_data:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_state",
                "error_description": "State not found or expired",
            },
        )

    callback_url = state_data["callback_url"]

    # Generate trace ID for Ares
    trace_id = str(uuid.uuid4())

    # Exchange code for tokens via Ares /login endpoint
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.auth_server_token_url,
                params={
                    "code": code,
                    "callback_url": callback_url,
                },
                headers={
                    settings.trace_id_header: trace_id,
                    "Content-Type": "application/json",
                },
            )

            if response.status_code != 200:
                # Error in token exchange - don't consume state to allow retries
                error_data = response.json() if response.content else {}
                return JSONResponse(
                    status_code=response.status_code,
                    content={
                        "error": error_data.get("error_message", "token_exchange_failed"),
                        "error_description": error_data.get("error_message", response.text),
                    },
                )

            # Success! Now consume the state to prevent replay attacks
            oauth_state_store.consume(state)

            # Return tokens
            tokens = response.json()
            return JSONResponse(content=tokens)

        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "server_error",
                    "error_description": str(e),
                },
            )


async def auth_refresh(request: Request) -> JSONResponse:
    """
    POST /auth/refresh - Refreshes access token using refresh_token.

    Body: { "refresh_token": "..." }
    """
    try:
        body = await request.json()
        refresh_token = body.get("refresh_token")
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "Invalid JSON body",
            },
        )

    if not refresh_token:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "Missing refresh_token in body",
            },
        )

    # Generate trace ID for Ares
    trace_id = str(uuid.uuid4())

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.auth_server_refresh_url,
                json={"refresh_token": refresh_token},
                headers={
                    settings.trace_id_header: trace_id,
                    "Content-Type": "application/json",
                },
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                return JSONResponse(
                    status_code=response.status_code,
                    content={
                        "error": error_data.get("error_message", "refresh_failed"),
                        "error_description": error_data.get("error_message", response.text),
                    },
                )

            return JSONResponse(content=response.json())

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "server_error",
                    "error_description": str(e),
                },
            )


def get_oauth_routes() -> List[Route]:
    """Return routes for fallback OAuth endpoints."""
    return [
        Route("/auth/start", endpoint=auth_start, methods=["GET"]),
        Route("/auth/callback", endpoint=auth_callback, methods=["GET"]),
        Route("/auth/refresh", endpoint=auth_refresh, methods=["POST"]),
    ]
