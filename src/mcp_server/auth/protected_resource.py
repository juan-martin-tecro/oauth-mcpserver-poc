"""RFC 9728 Protected Resource Metadata implementation."""

from typing import Dict, List, Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ..config import settings


def get_protected_resource_metadata() -> Dict[str, Any]:
    """
    Generate OAuth 2.0 Protected Resource Metadata per RFC 9728.

    This metadata document allows MCP clients to discover which
    authorization servers can issue tokens for this protected resource.

    Returns:
        dict: Metadata document for the protected resource
    """
    return {
        "resource": settings.server_url,
        "authorization_servers": [settings.auth_server_issuer],
        "scopes_supported": settings.supported_scopes,
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{settings.server_url}/docs",
    }


async def protected_resource_metadata_endpoint(request: Request) -> JSONResponse:
    """
    Handle GET /.well-known/oauth-protected-resource requests.

    Per RFC 9728, returns metadata about this protected resource
    including which authorization servers can issue tokens for it.
    """
    metadata = get_protected_resource_metadata()
    return JSONResponse(
        content=metadata,
        media_type="application/json",
    )


def get_protected_resource_routes() -> List[Route]:
    """Return routes for RFC 9728 Protected Resource Metadata."""
    return [
        Route(
            "/.well-known/oauth-protected-resource",
            endpoint=protected_resource_metadata_endpoint,
            methods=["GET"],
        ),
    ]


def get_www_authenticate_header(scope: str = None) -> str:
    """
    Generate WWW-Authenticate header value for 401 responses.

    Per RFC 9728 Section 5.1 and MCP spec requirements, the header
    includes a resource_metadata URL pointing to the protected resource
    metadata endpoint.

    Args:
        scope: Optional scope to include in the header

    Returns:
        str: WWW-Authenticate header value
    """
    metadata_url = f"{settings.server_url}/.well-known/oauth-protected-resource"

    header_value = f'Bearer resource_metadata="{metadata_url}"'

    if scope:
        header_value += f' scope="{scope}"'

    return header_value
