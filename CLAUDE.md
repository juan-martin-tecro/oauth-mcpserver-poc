# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Server implementing OAuth 2.1 Protected Resource (RFC 9728) that proxies authentication through an external authorization server (Ares) and validates JWTs issued by Auth0. The server exposes MCP tools that forward authenticated requests to the Otus API.

## Build and Run Commands

```bash
# Create/activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install with dev dependencies
pip install -e ".[dev]"

# Run server (development with hot reload)
uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000 --reload

# Run server (production mode)
python -m mcp_server.main

# Run tests
pytest

# Run single test file
pytest tests/test_example.py

# Linting
ruff check src/
```

## Architecture

```
MCP Client (Claude/Codex)
         |
         v
   Starlette App (main.py)
         |
         ├── BearerAuthMiddleware (validates JWT via Auth0 JWKS)
         |
         ├── /.well-known/* endpoints (RFC 9728/8414 metadata)
         ├── /oauth/* proxy endpoints (translate standard OAuth to Ares)
         ├── /auth/* fallback endpoints (manual OAuth flow)
         └── /mcp/* (FastMCP SSE transport, protected)
                  |
                  └── MCP Tools (e.g., otus_teams)
                            |
                            v
                      Otus API (/teams)
```

**Key Components:**

- `main.py` - Starlette application entry point, route configuration, middleware setup
- `server.py` - FastMCP server creation and tool registration
- `config.py` - Pydantic Settings loading from environment variables
- `auth/middleware.py` - BearerAuthMiddleware that protects `/mcp/*` routes
- `auth/token_verifier.py` - Auth0TokenVerifier validates JWTs using JWKS
- `auth/protected_resource.py` - RFC 9728 metadata endpoints and WWW-Authenticate header generation
- `oauth/proxy.py` - Translates standard OAuth 2.1 requests to Ares API format
- `oauth/routes.py` - Fallback OAuth endpoints for manual testing
- `oauth/state.py` - In-memory OAuth state storage
- `tools/otus_teams.py` - MCP tool that calls Otus API with forwarded bearer token
- `http_client/otus_client.py` - HTTP client for Otus API

**Authentication Flow:**

1. MCP client discovers server via `/.well-known/oauth-protected-resource`
2. Client gets auth server metadata from `/.well-known/oauth-authorization-server`
3. Client initiates OAuth via `/oauth/authorize` (proxied to Ares)
4. After auth, client exchanges code at `/oauth/token` (proxied to Ares)
5. Client calls `/mcp/sse` with Bearer token
6. Middleware validates JWT signature against Auth0 JWKS
7. Tools forward validated token to downstream APIs (Otus)

## Configuration

All configuration via environment variables (see `.env.example`):

- `SERVER_URL` - Canonical URL of this server (used in metadata)
- `AUTH_SERVER_*` - Ares OAuth endpoints
- `JWT_*` - Auth0 JWKS URL, issuer, audience for JWT validation
- `OTUS_*` - Otus API configuration
- `OAUTH_CLIENT_ID` - Client ID for fallback auth flow
