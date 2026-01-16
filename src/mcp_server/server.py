"""MCP Server setup with FastMCP."""

import logging
from typing import Tuple
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .config import settings
from .http_client.otus_client import OtusClient
from .tools.otus_teams import register_tools

logger = logging.getLogger(__name__)


def create_mcp_server() -> Tuple[FastMCP, OtusClient]:
    """
    Create and configure the MCP server.

    The server is configured as an OAuth 2.1 Protected Resource,
    requiring valid bearer tokens for tool invocations.

    Returns:
        Tuple of (FastMCP server instance, OtusClient instance)
    """
    # Create MCP server
    # Note: Authentication is handled by our custom middleware,
    # not by FastMCP's built-in auth. This gives us more control
    # over the WWW-Authenticate header format per RFC 9728.
    #
    # streamable_http_path="/" ensures endpoints are at the root of the mount point
    # so when mounted at /mcp, endpoints are at /mcp instead of /mcp/mcp
    #
    # Configure transport security to allow our production host
    # See: https://github.com/modelcontextprotocol/python-sdk/issues/1798
    parsed_url = urlparse(settings.server_url)
    server_host = parsed_url.netloc  # e.g., "oauth-mcpserver-poc.onrender.com"

    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "localhost:*",
            "127.0.0.1:*",
            f"{server_host}",
            f"{server_host}:*",
        ],
        allowed_origins=[
            "http://localhost:*",
            "https://localhost:*",
            f"https://{server_host}",
            "https://claude.ai",
            "https://claude.com",
        ],
    )

    mcp = FastMCP(
        name="oauth-mcp-server",
        streamable_http_path="/",
        transport_security=transport_security,
    )

    # Create HTTP client for Otus
    otus_client = OtusClient()

    # Register tools
    register_tools(mcp, otus_client)

    logger.info("MCP server created with otus_teams tool")

    return mcp, otus_client
