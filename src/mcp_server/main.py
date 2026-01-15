"""Application entry point - creates and configures the Starlette application."""

import logging
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .auth.middleware import BearerAuthMiddleware
from .auth.protected_resource import get_protected_resource_routes
from .auth.token_verifier import Auth0TokenVerifier
from .config import settings
from .oauth.client_registration import get_client_registration_routes
from .oauth.proxy import get_oauth_proxy_routes
from .oauth.routes import get_oauth_routes
from .server import create_mcp_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
mcp_server = None
otus_client = None


@asynccontextmanager
async def lifespan(app):
    """Application lifespan handler for startup/shutdown."""
    global mcp_server, otus_client

    # Startup
    logger.info("Starting MCP OAuth Server...")
    logger.info(f"Server URL: {settings.server_url}")
    logger.info(f"Auth Server: {settings.auth_server_issuer}")

    mcp_server, otus_client = create_mcp_server()
    await otus_client.start()

    logger.info("MCP OAuth Server ready")

    yield

    # Shutdown
    logger.info("Shutting down MCP OAuth Server...")
    await otus_client.stop()
    logger.info("Shutdown complete")


async def healthz(request: Request) -> JSONResponse:
    """
    Health check endpoint.

    Returns 200 OK if the server is running.
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "oauth-mcp-server",
            "version": "0.1.0",
        }
    )


async def root(request: Request) -> JSONResponse:
    """
    Root endpoint with server information.

    Provides links to important endpoints.
    """
    return JSONResponse(
        content={
            "name": "OAuth MCP Server",
            "version": "0.1.0",
            "description": "MCP Server acting as OAuth 2.1 Protected Resource",
            "endpoints": {
                "health": "/healthz",
                "protected_resource_metadata": "/.well-known/oauth-protected-resource",
                "authorization_server_metadata": "/.well-known/oauth-authorization-server",
                "client_registration": "/register",
                "oauth_authorize": "/oauth/authorize",
                "oauth_token": "/oauth/token",
                "mcp_sse": "/mcp/sse",
                "auth_start": "/auth/start",
                "auth_callback": "/auth/callback",
                "auth_refresh": "/auth/refresh",
            },
        }
    )


def create_app() -> Starlette:
    """
    Create the Starlette application with all routes and middleware.

    Returns:
        Configured Starlette application
    """
    global mcp_server, otus_client

    # Create MCP server and client (needed for route setup)
    mcp_server, otus_client = create_mcp_server()

    # Define routes
    routes = [
        # Root endpoint
        Route("/", endpoint=root, methods=["GET"]),
        # Health check (unprotected)
        Route("/healthz", endpoint=healthz, methods=["GET"]),
        # RFC 9728 Protected Resource Metadata (unprotected)
        *get_protected_resource_routes(),
        # RFC 7591 Dynamic Client Registration (unprotected)
        *get_client_registration_routes(),
        # OAuth proxy endpoints (unprotected) - translate standard OAuth to Ares
        *get_oauth_proxy_routes(),
        # Fallback OAuth endpoints (unprotected)
        *get_oauth_routes(),
        # MCP SSE transport (protected by middleware)
        Mount("/mcp", app=mcp_server.sse_app()),
    ]

    # Create application with lifespan handler
    app = Starlette(
        routes=routes,
        lifespan=lifespan,
    )

    # Add authentication middleware
    # The middleware will skip authentication for excluded paths
    app.add_middleware(
        BearerAuthMiddleware,
        token_verifier=Auth0TokenVerifier(),
        excluded_paths=[
            "/",
            "/.well-known/oauth-protected-resource",
            "/.well-known/oauth-authorization-server",
            "/healthz",
            "/register",
            "/oauth/authorize",
            "/oauth/token",
            "/auth/start",
            "/auth/callback",
            "/auth/refresh",
        ],
    )

    return app


# Create the application instance
app = create_app()


def main():
    """Run the server using uvicorn."""
    import uvicorn

    uvicorn.run(
        "mcp_server.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
