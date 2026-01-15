"""RFC 7591 OAuth 2.0 Dynamic Client Registration implementation."""

import secrets
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..config import settings


class ClientRegistrationRequest(BaseModel):
    """Client registration request per RFC 7591."""

    redirect_uris: List[str] = Field(..., description="Array of redirect URIs")
    token_endpoint_auth_method: str = Field(
        default="none", description="Authentication method for token endpoint"
    )
    grant_types: List[str] = Field(
        default=["authorization_code", "refresh_token"],
        description="Grant types the client will use",
    )
    response_types: List[str] = Field(
        default=["code"], description="Response types the client will use"
    )
    client_name: Optional[str] = Field(
        default=None, description="Human-readable name of the client"
    )
    client_uri: Optional[str] = Field(
        default=None, description="URL of the client's home page"
    )
    scope: Optional[str] = Field(
        default=None, description="Space-separated list of scopes"
    )


class ClientRegistrationResponse(BaseModel):
    """Client registration response per RFC 7591."""

    client_id: str
    client_secret: Optional[str] = None
    client_id_issued_at: int
    client_secret_expires_at: Optional[int] = None
    redirect_uris: List[str]
    token_endpoint_auth_method: str
    grant_types: List[str]
    response_types: List[str]
    client_name: Optional[str] = None
    client_uri: Optional[str] = None
    scope: Optional[str] = None


# In-memory client store (for POC - use a database in production)
_registered_clients: Dict[str, Dict[str, Any]] = {}


def generate_client_id() -> str:
    """Generate a unique client ID."""
    return f"mcp_client_{secrets.token_urlsafe(16)}"


def register_client(request_data: ClientRegistrationRequest) -> ClientRegistrationResponse:
    """
    Register a new OAuth client.

    Args:
        request_data: Client registration request data

    Returns:
        ClientRegistrationResponse with the registered client details
    """
    client_id = generate_client_id()
    issued_at = int(time.time())

    # For public clients (token_endpoint_auth_method=none), no secret is needed
    client_secret = None
    secret_expires_at = None

    if request_data.token_endpoint_auth_method != "none":
        client_secret = secrets.token_urlsafe(32)
        # Secret expires in 1 year
        secret_expires_at = issued_at + (365 * 24 * 60 * 60)

    # Build response
    response = ClientRegistrationResponse(
        client_id=client_id,
        client_secret=client_secret,
        client_id_issued_at=issued_at,
        client_secret_expires_at=secret_expires_at,
        redirect_uris=request_data.redirect_uris,
        token_endpoint_auth_method=request_data.token_endpoint_auth_method,
        grant_types=request_data.grant_types,
        response_types=request_data.response_types,
        client_name=request_data.client_name,
        client_uri=request_data.client_uri,
        scope=request_data.scope,
    )

    # Store client (in production, persist to database)
    _registered_clients[client_id] = response.model_dump()

    return response


async def client_registration_endpoint(request: Request) -> JSONResponse:
    """
    Handle POST /register requests for dynamic client registration.

    Per RFC 7591, this endpoint allows clients to register themselves
    dynamically without manual intervention.
    """
    try:
        body = await request.json()
        registration_request = ClientRegistrationRequest(**body)
        response = register_client(registration_request)

        return JSONResponse(
            content=response.model_dump(exclude_none=True),
            status_code=201,
            media_type="application/json",
        )
    except Exception as e:
        return JSONResponse(
            content={
                "error": "invalid_client_metadata",
                "error_description": str(e),
            },
            status_code=400,
            media_type="application/json",
        )


def get_client_registration_routes() -> List[Route]:
    """Return routes for RFC 7591 Dynamic Client Registration."""
    return [
        Route(
            "/register",
            endpoint=client_registration_endpoint,
            methods=["POST"],
        ),
    ]


def get_registered_client(client_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a registered client by ID.

    Args:
        client_id: The client ID to look up

    Returns:
        Client data if found, None otherwise
    """
    return _registered_clients.get(client_id)
