"""OAuth proxy endpoints to translate standard OAuth flow to Ares API."""

import logging
import uuid
from typing import List

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

from ..config import settings
from .state import oauth_state_store

logger = logging.getLogger(__name__)


async def oauth_authorize_proxy(request: Request) -> RedirectResponse:
    """
    GET /oauth/authorize - Proxy for OAuth authorization endpoint.

    Receives standard OAuth 2.1 authorization request (GET) and translates
    it to Ares API (POST), then redirects to the auth provider.

    Standard OAuth query params:
        response_type: Must be "code"
        client_id: The registered client ID
        redirect_uri: Where to redirect after auth
        state: CSRF protection state
        scope: Requested scopes
        code_challenge: PKCE challenge
        code_challenge_method: Must be "S256"
    """
    # Extract standard OAuth parameters
    response_type = request.query_params.get("response_type")
    client_id = request.query_params.get("client_id")
    redirect_uri = request.query_params.get("redirect_uri")
    state = request.query_params.get("state")
    scope = request.query_params.get("scope")
    code_challenge = request.query_params.get("code_challenge")
    code_challenge_method = request.query_params.get("code_challenge_method")

    # Validate required params
    if response_type != "code":
        return JSONResponse(
            status_code=400,
            content={
                "error": "unsupported_response_type",
                "error_description": "Only 'code' response_type is supported",
            },
        )

    if not redirect_uri or not state:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "Missing redirect_uri or state",
            },
        )

    # Store the original request params for the token exchange
    oauth_state_store.save(
        state,
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "scope": scope,
        },
    )

    # Generate trace ID for Ares
    trace_id = str(uuid.uuid4())

    # Call Ares /authorize endpoint (POST) to get the redirect URL
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                settings.auth_server_authorize_url,
                params={"callback_url": redirect_uri},
                headers={settings.trace_id_header: trace_id},
            )
            response.raise_for_status()
            data = response.json()
            auth_url = data.get("redirect_url")

            if not auth_url:
                logger.error(f"Ares response missing redirect_url: {data}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "server_error",
                        "error_description": "No redirect_url from authorization server",
                    },
                )

            # Ensure state is in the redirect URL for CSRF protection
            if "state=" not in auth_url:
                separator = "&" if "?" in auth_url else "?"
                auth_url = f"{auth_url}{separator}state={state}"

            logger.info(f"Redirecting to auth provider: {auth_url[:100]}...")
            return RedirectResponse(url=auth_url, status_code=302)

        except httpx.HTTPStatusError as e:
            logger.error(f"Ares authorize error: {e.response.status_code} - {e.response.text}")
            return JSONResponse(
                status_code=e.response.status_code,
                content={
                    "error": "authorization_error",
                    "error_description": f"Authorization server error: {e.response.text}",
                },
            )
        except Exception as e:
            logger.error(f"Failed to proxy authorize request: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "server_error",
                    "error_description": str(e),
                },
            )


async def oauth_token_proxy(request: Request) -> JSONResponse:
    """
    POST /oauth/token - Proxy for OAuth token endpoint.

    Receives standard OAuth 2.1 token request and translates it to Ares API.

    Standard OAuth body params (form-urlencoded):
        grant_type: "authorization_code" or "refresh_token"
        code: Authorization code (for authorization_code grant)
        redirect_uri: Must match the one used in authorize
        client_id: The registered client ID
        code_verifier: PKCE verifier (for authorization_code grant)
        refresh_token: Refresh token (for refresh_token grant)
    """
    # Parse form data or JSON
    content_type = request.headers.get("content-type", "")

    if "application/x-www-form-urlencoded" in content_type:
        form_data = await request.form()
        grant_type = form_data.get("grant_type")
        code = form_data.get("code")
        redirect_uri = form_data.get("redirect_uri")
        client_id = form_data.get("client_id")
        code_verifier = form_data.get("code_verifier")
        refresh_token = form_data.get("refresh_token")
    else:
        try:
            body = await request.json()
            grant_type = body.get("grant_type")
            code = body.get("code")
            redirect_uri = body.get("redirect_uri")
            client_id = body.get("client_id")
            code_verifier = body.get("code_verifier")
            refresh_token = body.get("refresh_token")
        except Exception:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "invalid_request",
                    "error_description": "Invalid request body",
                },
            )

    # Generate trace ID for Ares
    trace_id = str(uuid.uuid4())

    async with httpx.AsyncClient() as client:
        try:
            if grant_type == "authorization_code":
                # Exchange code for tokens via Ares /login endpoint
                response = await client.post(
                    settings.auth_server_token_url,
                    params={
                        "code": code,
                        "callback_url": redirect_uri,
                    },
                    headers={
                        settings.trace_id_header: trace_id,
                        "Content-Type": "application/json",
                    },
                )

            elif grant_type == "refresh_token":
                # Refresh tokens via Ares /refresh_token endpoint
                response = await client.post(
                    settings.auth_server_refresh_url,
                    json={"refresh_token": refresh_token},
                    headers={
                        settings.trace_id_header: trace_id,
                        "Content-Type": "application/json",
                    },
                )

            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "unsupported_grant_type",
                        "error_description": f"Grant type '{grant_type}' not supported",
                    },
                )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                logger.error(f"Ares token error: {response.status_code} - {error_data}")
                return JSONResponse(
                    status_code=response.status_code,
                    content={
                        "error": error_data.get("error", "token_error"),
                        "error_description": error_data.get("error_message", response.text),
                    },
                )

            # Return tokens in standard OAuth format
            tokens = response.json()

            # Ensure response has standard OAuth fields
            oauth_response = {
                "access_token": tokens.get("access_token"),
                "token_type": tokens.get("token_type", "Bearer"),
                "expires_in": tokens.get("expires_in", 3600),
            }

            if tokens.get("refresh_token"):
                oauth_response["refresh_token"] = tokens["refresh_token"]
            if tokens.get("id_token"):
                oauth_response["id_token"] = tokens["id_token"]
            if tokens.get("scope"):
                oauth_response["scope"] = tokens["scope"]

            return JSONResponse(content=oauth_response)

        except Exception as e:
            logger.error(f"Token proxy error: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "server_error",
                    "error_description": str(e),
                },
            )


def get_oauth_proxy_routes() -> List[Route]:
    """Return routes for OAuth proxy endpoints."""
    return [
        Route("/oauth/authorize", endpoint=oauth_authorize_proxy, methods=["GET"]),
        Route("/oauth/token", endpoint=oauth_token_proxy, methods=["POST"]),
    ]
