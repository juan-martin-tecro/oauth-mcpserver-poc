# MCP Server OAuth 2.1 Protected Resource

MCP Server en Python que actua como OAuth 2.1 Protected Resource, conforme a RFC 9728 y la especificacion MCP.

## Arquitectura

```
MCP Client (Claude/Codex)
         |
         v
   MCP Server (este POC)  -----> Otus API (/teams)
         |
         | JWT Validation
         v
   Auth0 (JWKS)     <-----     Ares (OAuth Broker)
```

## Requisitos

- Python 3.11+
- Acceso a Ares y Otus APIs

## Instalacion

```bash
# Clonar repositorio
cd oauth-mcpserver-poc

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate     # Windows

# Instalar dependencias
pip install -r requirements.txt

# Copiar y configurar variables de entorno
cp .env.example .env
# Editar .env con tu configuracion
```

## Configuracion

Editar `.env` con los valores apropiados:

```env
SERVER_URL=http://localhost:8000
OAUTH_CLIENT_ID=tu_client_id
```

## Ejecucion Local

```bash
# Opcion 1: Con uvicorn directamente
uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000 --reload

# Opcion 2: Con el modulo
python -m mcp_server.main
```

El servidor estara disponible en `http://localhost:8000`.

## Ejecucion con Docker

```bash
# Construir imagen
docker build -t oauth-mcp-server .

# Ejecutar contenedor
docker run -p 8000:8000 --env-file .env oauth-mcp-server
```

## Endpoints

| Endpoint | Metodo | Auth | Descripcion |
|----------|--------|------|-------------|
| `/` | GET | No | Info del servidor |
| `/healthz` | GET | No | Health check |
| `/.well-known/oauth-protected-resource` | GET | No | Metadata RFC 9728 |
| `/auth/start` | GET | No | Inicia OAuth flow |
| `/auth/callback` | GET | No | Callback OAuth |
| `/auth/refresh` | POST | No | Refresh token |
| `/mcp/sse` | GET | **Si** | MCP SSE transport |

## Verificacion con curl

### 1. Health Check

```bash
curl http://localhost:8000/healthz
```

### 2. Protected Resource Metadata (RFC 9728)

```bash
curl http://localhost:8000/.well-known/oauth-protected-resource
```

Respuesta:
```json
{
  "resource": "http://localhost:8000",
  "authorization_servers": ["https://tecro-api.tecrolabs.dev/ares"],
  "scopes_supported": ["openid", "profile", "email", "offline_access"],
  "bearer_methods_supported": ["header"]
}
```

### 3. Request sin token (debe retornar 401)

```bash
curl -i http://localhost:8000/mcp/sse
```

Respuesta esperada:
```
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Bearer resource_metadata="http://localhost:8000/.well-known/oauth-protected-resource" scope="openid profile email offline_access"

{"error":"unauthorized","error_description":"No valid bearer token provided"}
```

### 4. Request con token invalido (debe retornar 401)

```bash
curl -i -H "Authorization: Bearer invalid_token" http://localhost:8000/mcp/sse
```

### 5. Flujo OAuth Completo (Fallback)

```bash
# Paso 1: Iniciar flujo OAuth (abre en navegador)
curl -v http://localhost:8000/auth/start

# Paso 2: Despues de autenticar en el navegador, obtendras tokens en /auth/callback

# Paso 3: Usar el access_token
curl -H "Authorization: Bearer <ACCESS_TOKEN>" http://localhost:8000/mcp/sse
```

### 6. Refresh Token

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<REFRESH_TOKEN>"}'
```

## Tool MCP: otus_teams

La tool `otus_teams` permite obtener la lista de equipos desde Otus API.

### Uso desde MCP Client

Una vez autenticado, el MCP client puede invocar:

```json
{
  "method": "tools/call",
  "params": {
    "name": "otus_teams",
    "arguments": {}
  }
}
```

### Comportamiento

- **Token valido**: Retorna JSON de Otus `/teams`
- **Token invalido/expirado**: Error 401
- **Sin permisos**: Error 403

## Seguridad

- Los tokens se validan con JWKS de Auth0
- Se verifica: firma RS256, issuer, audience, expiracion
- Los tokens se forwardean a Otus sin modificacion
- NO se loguean tokens completos
- HTTPS obligatorio en produccion

## Estructura del Proyecto

```
oauth-mcpserver-poc/
├── src/mcp_server/
│   ├── auth/           # Autenticacion JWT y middleware
│   ├── oauth/          # Endpoints fallback OAuth
│   ├── tools/          # Tools MCP
│   ├── http_client/    # Cliente HTTP para Otus
│   ├── config.py       # Configuracion
│   ├── server.py       # Setup MCP server
│   └── main.py         # Entry point
├── tests/              # Tests
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Desarrollo

```bash
# Instalar dependencias de desarrollo
pip install -e ".[dev]"

# Ejecutar tests
pytest

# Linting
ruff check src/
```
