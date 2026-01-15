# Changelog: Mejora del Manejo de Estado OAuth

## Problema Resuelto

El estado OAuth se consumía inmediatamente al acceder al callback, incluso si el intercambio de tokens fallaba. Esto causaba problemas con:
- Reintentos en caso de errores
- Prefetch automático del navegador
- Clientes MCP como ChatGPT que pueden hacer múltiples requests

## Cambios Implementados

### 1. `src/mcp_server/oauth/state.py`

**Nuevos métodos:**
- `peek(state: str)` - Obtiene el estado sin consumirlo (permite validación y reintentos)
- `consume(state: str)` - Consume explícitamente el estado después de éxito

**Método deprecado:**
- `get(state: str)` - Mantenido para compatibilidad, pero marcado como deprecado

### 2. `src/mcp_server/oauth/routes.py` - `auth_callback()`

**Cambios:**
- Usa `peek()` en lugar de `get()` para obtener el estado sin consumirlo
- Solo consume el estado (`consume()`) después de un intercambio exitoso de tokens
- Si el intercambio falla, el estado permanece disponible para reintentos

## Beneficios

✅ **Reintentos permitidos**: Si el intercambio de tokens falla, el cliente puede reintentar
✅ **Idempotencia**: Múltiples requests al mismo callback funcionan correctamente
✅ **Compatibilidad con ChatGPT**: El prefetch del navegador no consume el estado prematuramente
✅ **Seguridad mantenida**: El estado sigue siendo single-use, pero solo después de éxito
✅ **Mejor experiencia de usuario**: Errores transitorios no invalidan el flujo completo

## Comportamiento Anterior vs. Nuevo

| Escenario | Antes | Ahora |
|-----------|-------|-------|
| Acceso al callback | ❌ Consume estado inmediatamente | ✅ Solo lee el estado |
| Intercambio exitoso | ✅ Funciona | ✅ Funciona + consume estado |
| Error en intercambio | ❌ Estado ya consumido, no se puede reintentar | ✅ Estado disponible para reintento |
| Prefetch del navegador | ❌ Consume estado, ChatGPT falla | ✅ No consume estado, ChatGPT funciona |
| Múltiples requests | ❌ Solo el primero funciona | ✅ Todos funcionan (idempotente) |

## Compatibilidad

- ✅ Compatible con código existente (método `get()` aún disponible)
- ✅ No requiere cambios en clientes OAuth
- ✅ Mejora la robustez sin cambiar la API externa

## Testing Recomendado

1. Probar flujo OAuth normal (debe funcionar igual)
2. Probar con error en intercambio de tokens (debe permitir reintento)
3. Probar con prefetch del navegador (debe funcionar)
4. Probar con múltiples requests simultáneos (debe ser idempotente)
