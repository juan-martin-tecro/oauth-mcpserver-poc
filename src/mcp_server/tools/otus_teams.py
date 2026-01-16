"""MCP Tool implementation for Otus teams endpoint."""

import logging

from mcp.server.fastmcp import FastMCP

from ..auth.context import get_current_token
from ..http_client.otus_client import OtusClient, OtusClientError

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, otus_client: OtusClient) -> None:
    """
    Register MCP tools with the server.

    Args:
        mcp: The FastMCP server instance
        otus_client: The Otus API client
    """

    @mcp.tool(
        name="ping",
        description="Simple ping tool to test MCP connectivity. Returns 'pong' with a timestamp.",
    )
    async def ping() -> str:
        """Simple ping tool for testing connectivity."""
        import datetime
        return f"pong - {datetime.datetime.now().isoformat()}"

    @mcp.tool(
        name="otus_teams",
        description="Retrieve teams from the Otus API. Returns a list of teams the authenticated user has access to.",
    )
    async def otus_teams() -> str:
        """
        Retrieve teams from the Otus API.

        This tool requires a valid bearer token in the request.
        The token is forwarded to the Otus API to authenticate the request.

        Returns:
            JSON string containing the teams data from Otus

        Raises:
            ValueError: If no authentication token is available
            OtusClientError: If Otus API returns an error
        """
        # Get the bearer token from the context variable
        # This was set by the BearerAuthMiddleware
        bearer_token = get_current_token()

        if not bearer_token:
            logger.error("No bearer token available in context")
            raise ValueError(
                "Authentication required. No valid bearer token available."
            )

        try:
            # Call Otus API with forwarded token
            result = await otus_client.get_teams(bearer_token)

            logger.debug("Successfully fetched teams from Otus")
            return result

        except OtusClientError as e:
            logger.error(f"Failed to fetch teams from Otus: {e}")
            # Re-raise with appropriate error for MCP
            if e.status_code == 401:
                raise ValueError("Token is invalid or expired") from e
            elif e.status_code == 403:
                raise ValueError("Insufficient permissions to access teams") from e
            else:
                raise ValueError(f"Otus API error: {e.message}") from e
