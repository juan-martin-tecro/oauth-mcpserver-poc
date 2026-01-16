"""MCP Server setup with FastMCP."""

import logging
from typing import Tuple

from mcp.server.fastmcp import FastMCP

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
    mcp = FastMCP(name="oauth-mcp-server", streamable_http_path="/")

    # Create HTTP client for Otus
    otus_client = OtusClient()

    # Register tools
    register_tools(mcp, otus_client)

    logger.info("MCP server created with otus_teams tool")

    return mcp, otus_client
