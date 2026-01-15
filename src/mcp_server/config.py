"""Configuration management using Pydantic Settings."""

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Server Configuration
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    server_url: str = Field(
        default="http://localhost:8000",
        description="The canonical URL of this MCP server (for resource identifier)",
    )

    # Authorization Server (Ares) Configuration
    auth_server_authorize_url: str = (
        "https://tecro-api.tecrolabs.dev/ares/api/authorize"
    )
    auth_server_token_url: str = "https://tecro-api.tecrolabs.dev/ares/api/login"
    auth_server_refresh_url: str = (
        "https://tecro-api.tecrolabs.dev/ares/api/refresh_token"
    )
    auth_server_issuer: str = "https://tecro-api.tecrolabs.dev/ares"

    # JWT Validation Configuration (Auth0)
    jwt_jwks_url: str = (
        "https://square-test-ttt.us.auth0.com/.well-known/jwks.json"
    )
    jwt_issuer: str = "https://square-test-ttt.us.auth0.com/"
    jwt_audience: str = "https://square-test-ttt.us.auth0.com/api/v2/"
    jwt_algorithms: List[str] = ["RS256"]
    jwt_custom_claims_namespace: str = "https://ares/"

    # OAuth Scopes
    supported_scopes: List[str] = ["openid", "profile", "email", "offline_access"]

    # Otus API Configuration
    otus_base_url: str = "https://tecro-api.tecrolabs.dev/otus"
    otus_teams_endpoint: str = "/teams"

    # OAuth Client Configuration (for fallback auth endpoints)
    oauth_client_id: str = Field(
        default="",
        description="OAuth client ID for fallback auth endpoints",
    )
    oauth_redirect_uri: str = Field(
        default="http://localhost:8000/auth/callback",
        description="OAuth redirect URI for fallback auth endpoints",
    )

    # Trace ID header name (required by Ares)
    trace_id_header: str = "Trace-Id"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }

    @property
    def otus_teams_url(self) -> str:
        """Full URL for Otus teams endpoint."""
        return f"{self.otus_base_url}{self.otus_teams_endpoint}"


# Singleton instance
settings = Settings()
