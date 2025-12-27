# Error Log & Solutions

This document tracks errors encountered during development and deployment, along with their solutions. Use this to quickly diagnose and fix recurring issues.

---

## Table of Contents
1. [Database/SQLAlchemy Errors](#databasesqlalchemy-errors)
2. [Frontend/React Errors](#frontendreact-errors)
3. [API Errors](#api-errors)
4. [Deployment Errors](#deployment-errors)
5. [Redis/Connection Errors](#redisconnection-errors)
6. [SIP/Network Errors](#sipnetwork-errors)

---

## Database/SQLAlchemy Errors

### ERR-001: SQLEnum vs String Type Mismatch

**Date**: 2025-12-25

**Symptoms**:
- API returns 500 error when accessing Voice Agent endpoints
- Error in logs: Type mismatch between Python enum and database column

**Root Cause**:
The SQLAlchemy model used `SQLEnum(EnumClass)` for a column, but the Alembic migration created it as `sa.String()`. SQLAlchemy expects the types to match.

**Files Affected**:
- `backend/app/models/voice_agent.py`
- `backend/alembic/versions/013_add_voice_agent_tables.py`

**Bad Code**:
```python
# Model using SQLEnum
from sqlalchemy import Enum as SQLEnum

status: Mapped[VoiceAgentStatus] = mapped_column(
    SQLEnum(VoiceAgentStatus), default=VoiceAgentStatus.DRAFT
)
```

```python
# Migration using String
sa.Column('status', sa.String(20), default='draft')
```

**Solution**:
Either make both use SQLEnum OR both use String. We chose String for flexibility:

```python
# Model using String (matches migration)
status: Mapped[str] = mapped_column(
    String(20), default=VoiceAgentStatus.DRAFT.value
)
```

**Prevention**:
- Always verify that model column types match migration column types
- Prefer String over SQLEnum for status fields (more flexible, easier migrations)
- When using String for enum-like values, use `.value` when assigning

---

## Frontend/React Errors

### ERR-002: Radix UI SelectItem Empty Value

**Date**: 2025-12-25

**Symptoms**:
- Page renders blank/white
- Console error: `A <Select.Item /> must have a value prop that is not an empty string`
- Component crashes on render

**Root Cause**:
Radix UI's Select component uses empty string (`""`) as a special value to clear selection. Having a SelectItem with `value=""` conflicts with this behavior.

**Files Affected**:
- `frontend/src/components/settings/TestCallSettings.tsx`
- Any component using `@radix-ui/react-select` or shadcn's Select

**Bad Code**:
```tsx
<SelectItem value="">No audio (silence)</SelectItem>
<SelectItem value="">No audio (hang up)</SelectItem>
```

**Solution**:
Use a non-empty placeholder value like `"none"`:

```tsx
<SelectItem value="none">No audio (silence)</SelectItem>
<SelectItem value="none">No audio (hang up)</SelectItem>
```

Then handle it in the submit logic:
```tsx
const handleSubmit = () => {
  mutate({
    audio_file: audioFileId && audioFileId !== 'none' ? audioFileId : undefined,
  });
};
```

**Prevention**:
- Never use `value=""` in SelectItem components
- Use descriptive placeholder values like `"none"`, `"default"`, `"unset"`
- Always handle these placeholder values in form submission

---

## API Errors

### ERR-003: Enum Value Assignment in API Endpoints

**Date**: 2025-12-25

**Symptoms**:
- 500 error when creating/updating Voice Agent
- Type error in logs about enum vs string

**Root Cause**:
When the model uses String type for a field but the API code assigns an Enum directly (not its `.value`), SQLAlchemy can't store it.

**Files Affected**:
- `backend/app/api/v1/endpoints/voice_agent.py`

**Bad Code**:
```python
# Assigning enum directly to a String column
agent.status = VoiceAgentStatus.ACTIVE
```

**Solution**:
Use `.value` to get the string representation:

```python
# Assign the string value
agent.status = VoiceAgentStatus.ACTIVE.value
```

**Prevention**:
- When model uses String type for enum-like fields, always use `.value`
- Add type hints to catch these at development time
- Consider creating helper methods: `agent.set_status(VoiceAgentStatus.ACTIVE)`

---

## Deployment Errors

### ERR-004: Alembic Migration Duplicate Revision

**Date**: 2025-12-25

**Symptoms**:
- Alembic error: `Multiple head revisions`
- Deployment fails during database migration

**Root Cause**:
Two migration files have the same revision number or conflicting `down_revision` values, creating a branch in the migration tree.

**Solution**:
1. List all migrations: `alembic history`
2. Identify the conflict
3. Update the `down_revision` in the newer migration to point to the correct previous migration
4. Or merge heads: `alembic merge heads -m "merge"`

**Prevention**:
- Always pull latest changes before creating new migrations
- Use descriptive revision IDs (not auto-generated)
- Run `alembic check` before committing migrations

---

### ERR-005: FastAPI Route Ordering (Static vs Parameterized)

**Date**: 2025-12-25

**Symptoms**:
- API returns 404 for valid static paths like `/routes`, `/stats`, `/conversations`
- Error in browser: `GET /api/v1/voice-agents/routes 404 (Not Found)`
- Routes work when accessed with explicit IDs but fail for static paths

**Root Cause**:
FastAPI matches routes in definition order. If a parameterized route like `/{agent_id}` is defined before static routes like `/routes`, the static path will be treated as a parameter value.

Example: `/voice-agents/routes` matches `/{agent_id}` with `agent_id="routes"`, returning 404 because no agent with ID "routes" exists.

**Files Affected**:
- `backend/app/api/v1/endpoints/voice_agent.py`

**Bad Code**:
```python
router = APIRouter(prefix="/voice-agents")

@router.get("/{agent_id}")  # This catches EVERYTHING, including /routes
async def get_voice_agent(agent_id: str): ...

@router.get("/routes")  # This is NEVER reached!
async def list_routes(): ...
```

**Solution**:
Define static paths BEFORE parameterized paths:

```python
router = APIRouter(prefix="/voice-agents")

# Static paths FIRST
@router.get("/routes")
async def list_routes(): ...

@router.get("/stats")
async def get_stats(): ...

@router.get("/conversations")
async def list_conversations(): ...

# Parameterized paths LAST
@router.get("/{agent_id}")
async def get_voice_agent(agent_id: str): ...
```

**Prevention**:
- Always define static routes before parameterized routes in the same router
- Add a comment at the top of files with this pattern as a reminder
- Consider using more specific path prefixes (e.g., `/agent/{id}` instead of `/{id}`)
- Test all static endpoints after adding new parameterized routes

---

## Quick Diagnosis Checklist

### API Returns 500
1. Check API logs for stack trace
2. Common causes:
   - Database type mismatch (see ERR-001)
   - Enum value assignment (see ERR-003)
   - Missing required fields
   - Database connection issues

### Frontend Page Blank
1. Check browser console for errors
2. Common causes:
   - SelectItem empty value (see ERR-002)
   - Missing required props
   - API data shape mismatch
   - Uncaught Promise rejection

### API Returns 404 (Unexpected)
1. Check route ordering in endpoint file
2. Common causes:
   - Static path defined after parameterized path (see ERR-005)
   - Missing router include in main router
   - Incorrect path prefix

### Database Migration Fails
1. Check Alembic output
2. Common causes:
   - Duplicate revision (see ERR-004)
   - Column already exists
   - Foreign key constraint violation

### Redis/Pub-Sub Connection Issues
1. Check dialer-engine logs for "Connection closed by server"
2. Common causes:
   - Missing keepalive configuration (see ERR-006)
   - SSL certificate verification issues with DO Managed Redis
   - Idle timeout from managed Redis service

### SIP Status Not Updating
1. Check if dialer is registered (logs show "SIP registration successful")
2. Check Redis connection (pub/sub might be dropping)
3. Check WebSocket connection in browser console
4. Fallback: Dashboard polls `/settings/dialer/status` every 10-30 seconds

### SIP Test Shows "UCM did not respond to OPTIONS probe"
1. This warning is **normal** if dialer is registered
2. Check if overall test result is `success=True` (it should be)
3. The OPTIONS probe is sent from API server (different IP than dialer)
4. UCM may ignore OPTIONS from non-registered sources
5. If test fails completely, check Redis for `dialer:sip_status` key expiry

### Inbound Calls Not Working
1. Check if using DO App Platform (see ERR-007 - **architectural limitation**)
2. Workers cannot receive inbound UDP/TCP connections
3. Solution: Migrate dialer-engine to DOKS or Droplet with static IP

---

## Redis/Connection Errors

### ERR-006: DigitalOcean Managed Redis/Valkey Connection Drops

**Date**: 2025-12-25 (updated 2025-12-27)

**Symptoms**:
- Redis pubsub listener disconnects every ~5 minutes
- Logs show: "Connection closed by server.. Reconnecting in 5 seconds..."
- Dashboard SIP status not updating
- SIP test may fail even when dialer is registered

**Root Cause**:
DigitalOcean Managed Redis/Valkey has a **300-second (5-minute) idle timeout**. The pubsub connection sits idle waiting for messages - it only receives, never sends. After 5 minutes of no outbound traffic, the server closes it.

**Critical Issue**: The main Redis client and pubsub use **separate connections**. Pinging the main client does NOT keep the pubsub connection alive.

**Files Affected**:
- `backend/dialer/main.py`
- `backend/app/db/redis.py`
- `backend/app/services/connection_test_service.py`

**Bad Code**:
```python
# Redis client without keepalive
redis.from_url(redis_url, decode_responses=True)

# Keepalive only pings main client, NOT pubsub (STILL BREAKS!)
r = self._get_redis_client()
pubsub = r.pubsub()
await pubsub.subscribe("channel")
keepalive_task = asyncio.create_task(self._redis_keepalive(r, stop_event))  # Only pings 'r'!
```

**Solution**:
1. Add `socket_keepalive=True` and `health_check_interval=30` to all Redis clients:

```python
# Redis client with keepalive (prevents idle timeout)
redis.from_url(
    redis_url,
    decode_responses=True,
    socket_keepalive=True,
    health_check_interval=30  # Ping every 30 seconds
)
```

2. **Critical**: For pub/sub listeners, ping BOTH the main client AND the pubsub connection:

```python
async def _redis_keepalive(self, redis_client, stop_event, pubsub=None):
    """Send periodic pings to keep Redis connection alive."""
    ping_count = 0
    while not stop_event.is_set():
        await asyncio.sleep(60)  # Ping every 60 seconds
        if not stop_event.is_set():
            await redis_client.ping()
            ping_count += 1
            logger.info(f"Redis keepalive ping #{ping_count} successful")

            # CRITICAL: Also ping pubsub connection!
            # This prevents DO Valkey 5-minute idle timeout on pubsub
            if pubsub:
                await pubsub.ping()
                logger.debug(f"Pubsub keepalive ping #{ping_count} successful")

# Usage - pass pubsub to keepalive task
r = self._get_redis_client()
pubsub = r.pubsub()
await pubsub.subscribe("channel")
keepalive_task = asyncio.create_task(self._redis_keepalive(r, stop_event, pubsub=pubsub))
```

**Prevention**:
- Always use `socket_keepalive=True` for Redis connections
- Always use `health_check_interval=30` for production
- For SSL Redis (`rediss://`), also add `ssl_cert_reqs=None` for DO Managed Redis
- **For pubsub**: Always ping the pubsub connection itself, not just the main client
- Remember: pubsub uses a separate connection that doesn't benefit from main client pings

**Fix Applied**: v2.2.1 (commit 88deeb2) - 2025-12-27

---

## SIP/Network Errors

### ERR-007: DO App Platform Cannot Receive Inbound SIP Connections

**Date**: 2025-12-27

**Symptoms**:
- Outbound calls work perfectly (dialer → UCM → phone)
- Inbound calls never reach the dialer
- SIP test shows "⚠ UCM did not respond to OPTIONS probe" (this is normal)
- Dialer IS registered with UCM but cannot receive INVITE packets
- Dashboard shows dialer as "registered" but inbound routes don't work

**Root Cause**:
DigitalOcean App Platform **workers cannot receive inbound connections**. The platform only provides:
- **Egress**: Dedicated IP for outbound connections (works for SIP registration)
- **Ingress**: HTTP-only routing to services (paths `/` and `/api`)

SIP requires bidirectional UDP/TCP connectivity:
```
OUTBOUND (WORKS):
  dialer-engine ──REGISTER──> UCM ──INVITE──> Phone
                ──INVITE────>

INBOUND (BLOCKED):
  dialer-engine <──INVITE──✗ UCM <────────── Phone
         ↑
   Workers have NO inbound connectivity!
   UCM cannot send INVITE to the dialer.
```

**Files Affected**:
- `backend/dialer/main.py` (dialer-engine worker)
- `backend/dialer/voice_agent/inbound_handler.py` (never receives calls)
- App Platform spec (`egress: DEDICATED_IP` is outbound only)

**Current Architecture (Broken for Inbound)**:
```yaml
# App Platform spec
workers:
  - name: dialer-engine      # Workers have NO ingress!
    ...
egress:
  type: DEDICATED_IP         # Only for OUTBOUND connections
ingress:
  rules:
    - path: /                # HTTP only, goes to frontend
    - path: /api             # HTTP only, goes to api
    # No SIP/UDP/TCP ingress possible!
```

**Solution: Migrate to DOKS with NGINX Ingress + Floating IP**

DigitalOcean Kubernetes Service (DOKS) supports TCP/UDP ingress via Load Balancer.

**Step 1: Create DOKS Cluster**
```bash
doctl kubernetes cluster create sip-dialer-cluster \
  --region nyc1 \
  --size s-2vcpu-4gb \
  --count 2
```

**Step 2: Install NGINX Ingress Controller**
```bash
# Via Helm
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer

# Verify Load Balancer IP
kubectl get svc -n ingress-nginx
# NAME                       TYPE           EXTERNAL-IP
# ingress-nginx-controller   LoadBalancer   xxx.xxx.xxx.xxx
```

**Step 3: Create Floating IP for Static Address**
```bash
# Create Floating IP
doctl compute floating-ip create --region nyc1

# Note the IP address returned, e.g., 167.99.xxx.xxx

# Attach to Load Balancer (get LB ID from DO console)
doctl compute floating-ip-action assign <floating-ip> <load-balancer-id>
```

**Step 4: Configure TCP Ingress for SIP**
```yaml
# tcp-services-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tcp-services
  namespace: ingress-nginx
data:
  "5061": "default/dialer-engine:5061"  # TLS SIP
  "5060": "default/dialer-engine:5060"  # UDP SIP (if needed)
```

```yaml
# dialer-engine-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: dialer-engine
spec:
  selector:
    app: dialer-engine
  ports:
    - name: sip-tls
      port: 5061
      targetPort: 5061
      protocol: TCP
    - name: sip-udp
      port: 5060
      targetPort: 5060
      protocol: UDP
```

**Step 5: Update UCM Configuration**
```
SIP Server: <floating-ip>
SIP Port: 5061
Transport: TLS
```

**Alternative Solutions**:

| Option | Complexity | Cost | Notes |
|--------|------------|------|-------|
| **DOKS + Floating IP** | Medium | ~$20/mo | Full control, static IP, recommended |
| **Droplet** | Low | ~$6/mo | Simple, dedicated server for dialer |
| **SIP Trunk Provider** | Low | Per-min | Twilio/Telnyx accepts inbound, forwards via API |
| **Outbound Only** | None | $0 | Accept limitation, campaigns still work |

**Prevention**:
- When deploying SIP applications, verify platform supports UDP/TCP ingress
- DO App Platform is designed for HTTP workloads, not raw TCP/UDP
- For VoIP/SIP, always use: Droplets, DOKS, or dedicated VoIP infrastructure
- Document inbound call requirements early in architecture planning

**Status**: Architecture limitation identified. Migration to DOKS recommended.

---

## Adding New Errors

When documenting a new error, include:

1. **Error ID**: ERR-XXX (sequential)
2. **Date**: When first encountered
3. **Symptoms**: What the user/developer sees
4. **Root Cause**: Why it happens
5. **Files Affected**: Which files have the bug
6. **Bad Code**: Example of problematic code
7. **Solution**: How to fix it
8. **Prevention**: How to avoid it in the future
