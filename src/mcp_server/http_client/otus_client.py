"""Async HTTP client for Otus API calls."""

import logging
from typing import Optional

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class OtusClientError(Exception):
    """Exception raised when Otus API call fails."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Otus API error {status_code}: {message}")


class OtusClient:
    """
    Async HTTP client for Otus API calls.

    This client is used to forward authenticated requests to the Otus API,
    passing through the bearer token for authorization.
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            follow_redirects=False,  # Don't follow redirects to prevent token leakage
        )
        logger.info("Otus HTTP client initialized")

    async def stop(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Otus HTTP client closed")

    async def get_teams(self, bearer_token: str) -> str:
        """
        Fetch teams from Otus API.

        Args:
            bearer_token: Valid JWT to forward to Otus

        Returns:
            JSON string response from Otus (exact response, not parsed)

        Raises:
            OtusClientError: If Otus returns non-2xx status
            RuntimeError: If client is not initialized
        """
        if not self._client:
            raise RuntimeError("OtusClient not initialized. Call start() first.")

        url = settings.otus_teams_url
        logger.debug(f"Fetching teams from Otus: {url}")

        try:
            response = await self._client.get(
                url,
                headers={
                    "Authorization": f"Bearer {bearer_token}",
                    "Accept": "application/json",
                },
            )

            # Handle specific error cases
            if response.status_code == 401:
                logger.warning("Otus returned 401 - token may be invalid or expired")
                raise OtusClientError(401, "Unauthorized - invalid or expired token")

            if response.status_code == 403:
                logger.warning("Otus returned 403 - insufficient permissions")
                raise OtusClientError(403, "Forbidden - insufficient permissions")

            # Raise for other 4xx/5xx errors
            response.raise_for_status()

            # Return raw JSON text (preserve exact response)
            return response.text

        except httpx.HTTPStatusError as e:
            logger.error(f"Otus API error: {e.response.status_code}")
            raise OtusClientError(
                e.response.status_code,
                e.response.text or str(e),
            )
        except httpx.RequestError as e:
            logger.error(f"Otus request failed: {e}")
            raise OtusClientError(502, f"Failed to connect to Otus: {e}")
