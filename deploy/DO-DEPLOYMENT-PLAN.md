# SIP-Dialer SaaS Deployment Plan

## Overview
Deploy SIP-Dialer as a SaaS application on Digital Ocean App Platform, with IPsec VPN connection to on-premise UCM6302 via UniFi UDM Pro.

**Region:** NYC1 (New York)
**Branch:** deploy/digitalocean (pushed to GitHub)
**Repo:** github.com/sirsmithdev/Sip-Dialer
**MCP:** Using DigitalOcean MCP for automated deployment

---

## Deployment via DO MCP (Automated)

### Step 1: Create VPN Gateway Droplet
```
Create Ubuntu 22.04 droplet in NYC1
- Name: sip-dialer-vpn
- Size: s-1vcpu-1gb ($6/mo)
- Enable backups
```

### Step 2: Create Managed PostgreSQL
```
Create PostgreSQL 15 cluster in NYC1
- Name: sip-dialer-db
- Size: db-s-1vcpu-1gb ($15/mo)
```

### Step 3: Create Managed Redis
```
Create Redis 7 cluster in NYC1
- Name: sip-dialer-redis
- Size: db-s-1vcpu-1gb ($15/mo)
```

### Step 4: Create Spaces Bucket
```
Create Spaces bucket in NYC3
- Name: sip-dialer-audio
```

### Step 5: Deploy App Platform from GitHub
```
Deploy from sirsmithdev/Sip-Dialer branch deploy/digitalocean
Using app.yaml specification
```

### Step 6: Provide UniFi IPsec VPN Settings
After droplet is created, provide complete settings for UniFi UDM Pro:
- Remote Gateway IP (droplet public IP)
- Remote Networks (10.10.10.0/24)
- Pre-shared Key (generated)
- IKE/ESP encryption settings

---

## UniFi UDM Pro VPN Configuration (Manual Step)

Once the VPN Gateway Droplet is created, use these settings in UniFi:

| Setting | Value |
|---------|-------|
| **VPN Type** | Site-to-Site / Manual IPsec |
| **Remote Gateway** | `<DROPLET_PUBLIC_IP>` (provided after creation) |
| **Remote Networks** | `10.10.10.0/24` |
| **Pre-shared Key** | `<GENERATED_PSK>` (provided after creation) |
| **Key Exchange Version** | IKEv2 |
| **IKE Encryption** | AES-256 |
| **IKE Hash** | SHA-256 |
| **IKE DH Group** | 14 (2048-bit) |
| **ESP Encryption** | AES-256 |
| **ESP Hash** | SHA-256 |
| **ESP DH Group** | 14 (2048-bit) |
| **IKE Lifetime** | 28800 seconds |
| **ESP Lifetime** | 3600 seconds |

**Steps in UniFi Controller:**
1. Go to Settings → VPN → Site-to-Site VPN
2. Click "Create New" → "Manual IPsec"
3. Enter the values from the table above
4. Save and enable the VPN
5. Verify tunnel status shows "Established"

---

## Phase 1: IPsec VPN Setup (DO ↔ UniFi UDM Pro)

### 1.1 Create Digital Ocean Droplet (VPN Gateway)
- Create Ubuntu 22.04 droplet (smallest size, e.g., $6/mo)
- This droplet acts as VPN gateway to your local network
- Note the public IP address

### 1.2 Configure strongSwan on DO Droplet

```bash
# Install strongSwan
apt update && apt install -y strongswan strongswan-pki libcharon-extra-plugins

# Enable IP forwarding
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
sysctl -p
```

**`/etc/ipsec.conf`**:
```
config setup
    charondebug="ike 2, knl 2, cfg 2"

conn unifi-tunnel
    type=tunnel
    auto=start
    keyexchange=ikev2
    authby=secret

    # Force UDP encapsulation (required for DO)
    forceencaps=yes

    # DO Droplet (left = local)
    left=%defaultroute
    leftid=<DO_DROPLET_PUBLIC_IP>
    leftsubnet=10.10.10.0/24

    # UniFi UDM Pro (right = remote)
    right=<YOUR_STATIC_PUBLIC_IP>
    rightid=<YOUR_STATIC_PUBLIC_IP>
    rightsubnet=192.168.150.0/24

    # Encryption (match UniFi settings)
    ike=aes256-sha256-modp2048!
    esp=aes256-sha256!

    # Timeouts
    ikelifetime=28800s
    lifetime=3600s
    dpdaction=restart
    dpddelay=30s
```

**`/etc/ipsec.secrets`**:
```
<DO_DROPLET_IP> <YOUR_PUBLIC_IP> : PSK "your-strong-pre-shared-key-here"
```

### 1.3 Configure DO Firewall
- Allow inbound UDP 500 (IKE)
- Allow inbound UDP 4500 (NAT-T)

### 1.4 Configure UniFi UDM Pro

1. UniFi Network → Settings → VPN → Site-to-Site VPN
2. Create Manual IPsec:
   - **VPN Type**: Site-to-Site
   - **Remote Gateway IP**: DO Droplet public IP
   - **Remote Networks**: 10.10.10.0/24
   - **Pre-shared Key**: Same as ipsec.secrets
   - **IPsec Profile**: Customized
     - IKE Version: IKEv2
     - Encryption: AES-256
     - Hash: SHA-256
     - DH Group: 14 (modp2048)

### 1.5 Verify VPN Connection
```bash
# On DO Droplet
ipsec status
ping 192.168.150.10  # UCM6302 IP
```

---

## Phase 2: Digital Ocean App Platform Setup

### 2.1 Create Managed Services
- **PostgreSQL**: Managed Database ($15/mo starter)
- **Redis**: Managed Redis ($15/mo starter)
- **Spaces**: S3-compatible storage for audio files

### 2.2 App Platform Configuration (`app.yaml`)

```yaml
name: sip-dialer
region: nyc

services:
  # Frontend (React + Nginx)
  - name: frontend
    source_dir: /frontend
    dockerfile_path: Dockerfile
    http_port: 80
    instance_count: 1
    instance_size_slug: basic-xxs
    routes:
      - path: /
    health_check:
      http_path: /

  # API Gateway (FastAPI)
  - name: api
    source_dir: /backend
    dockerfile_path: Dockerfile.api
    http_port: 8000
    instance_count: 1
    instance_size_slug: basic-xs
    routes:
      - path: /api
    health_check:
      http_path: /api/v1/health
    envs:
      - key: DATABASE_URL
        scope: RUN_TIME
        value: ${db.DATABASE_URL}
      - key: REDIS_URL
        scope: RUN_TIME
        value: ${redis.REDIS_URL}

  # Celery Worker
  - name: worker
    source_dir: /backend
    dockerfile_path: Dockerfile.worker
    instance_count: 1
    instance_size_slug: basic-xs
    envs:
      - key: DATABASE_URL
        scope: RUN_TIME
        value: ${db.DATABASE_URL}
      - key: CELERY_BROKER_URL
        scope: RUN_TIME
        value: ${redis.REDIS_URL}

  # Celery Beat (Scheduler)
  - name: scheduler
    source_dir: /backend
    dockerfile_path: Dockerfile.beat
    instance_count: 1
    instance_size_slug: basic-xxs

databases:
  - name: db
    engine: PG
    version: "15"

  - name: redis
    engine: REDIS
```

### 2.3 Dialer Engine Deployment (Separate Droplet)

The dialer engine requires:
- Access to UCM via VPN (UDP ports for SIP/RTP)
- Cannot run on App Platform (needs raw UDP, host networking)

**Deploy on VPN Gateway Droplet or separate droplet on same VPC:**

```bash
# On the VPN gateway droplet (or new droplet with VPN access)
docker run -d \
  --name dialer-engine \
  --network host \
  -e SIP_SERVER=192.168.1.x \
  -e SIP_PORT=5060 \
  -e API_URL=https://api.yourdomain.com \
  sip-dialer/dialer:latest
```

---

## Phase 3: Environment Variables & Secrets

### Required Secrets (set in DO App Platform)
```
# Database (auto-injected from managed DB)
DATABASE_URL=postgresql+asyncpg://...

# Redis (auto-injected from managed Redis)
REDIS_URL=redis://...
CELERY_BROKER_URL=redis://...

# Security
JWT_SECRET_KEY=<generate-32-char-random>
ENCRYPTION_KEY=<generate-fernet-key>

# SIP (for dialer engine)
SIP_SERVER=192.168.150.10  # UCM IP via VPN
SIP_PORT=5060
SIP_USERNAME=<extension>
SIP_PASSWORD=<password>

# S3/Spaces
S3_ENDPOINT=https://nyc3.digitaloceanspaces.com
S3_ACCESS_KEY=<spaces-key>
S3_SECRET_KEY=<spaces-secret>
S3_BUCKET=sip-dialer-audio

# SMTP
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=<sendgrid-api-key>

# App
CORS_ORIGINS=https://yourdomain.com
APP_ENV=production
```

---

## Phase 4: DNS & SSL

1. Point domain to DO App Platform
2. SSL certificates auto-provisioned by DO
3. Configure CORS for frontend domain

---

## Phase 5: Files to Create/Modify

### New Dockerfiles needed:

| File | Purpose |
|------|---------|
| `frontend/Dockerfile` | Build React, serve with Nginx |
| `backend/Dockerfile.api` | FastAPI with uvicorn |
| `backend/Dockerfile.worker` | Celery worker |
| `backend/Dockerfile.beat` | Celery beat scheduler |
| `backend/Dockerfile.dialer` | Dialer engine (for droplet) |
| `app.yaml` | DO App Platform spec |

### Config updates:

| File | Changes |
|------|---------|
| `backend/app/core/config.py` | Add S3/Spaces config |
| `backend/app/services/storage.py` | Switch MinIO → DO Spaces |
| `docker-compose.prod.yml` | Production compose for dialer |

---

## Architecture Diagram

```
                    ┌─────────────────────────────────────────┐
                    │         Digital Ocean Cloud             │
                    │                                         │
┌─────────┐         │  ┌─────────────┐    ┌──────────────┐   │
│  Users  │────────►│  │  Frontend   │    │   Managed    │   │
│ (Web)   │         │  │  (App Plat) │    │   Postgres   │   │
└─────────┘         │  └──────┬──────┘    └──────────────┘   │
                    │         │                   ▲           │
                    │         ▼                   │           │
                    │  ┌─────────────┐    ┌──────┴───────┐   │
                    │  │  API + WS   │───►│   Managed    │   │
                    │  │  (App Plat) │    │    Redis     │   │
                    │  └──────┬──────┘    └──────────────┘   │
                    │         │                               │
                    │         ▼                               │
                    │  ┌─────────────┐    ┌──────────────┐   │
                    │  │   Workers   │    │  DO Spaces   │   │
                    │  │  (App Plat) │    │   (Audio)    │   │
                    │  └─────────────┘    └──────────────┘   │
                    │                                         │
                    │  ┌─────────────────────────────────┐   │
                    │  │     VPN Gateway Droplet         │   │
                    │  │  ┌───────────┐  ┌────────────┐  │   │
                    │  │  │strongSwan │  │  Dialer    │  │   │
                    │  │  │  (IPsec)  │  │  Engine    │  │   │
                    │  │  └─────┬─────┘  └─────┬──────┘  │   │
                    │  └────────┼──────────────┼─────────┘   │
                    └───────────┼──────────────┼─────────────┘
                                │              │
                         IPsec VPN Tunnel      │ SIP/RTP
                                │              │
                    ┌───────────┼──────────────┼─────────────┐
                    │           ▼              ▼             │
                    │     ┌──────────┐   ┌──────────┐       │
                    │     │   UDM    │───│  UCM6302 │       │
                    │     │   Pro    │   │   PBX    │       │
                    │     └──────────┘   └──────────┘       │
                    │                                        │
                    │         Your Local Network             │
                    └────────────────────────────────────────┘
```

---

## Estimated Monthly Costs

| Service | Cost |
|---------|------|
| App Platform (3 services) | ~$17/mo |
| Managed PostgreSQL | $15/mo |
| Managed Redis | $15/mo |
| VPN Gateway Droplet | $6/mo |
| DO Spaces (25GB) | $5/mo |
| **Total** | **~$58/mo** |

---

## Implementation Order

### Step 1: Create VPN Gateway Droplet
- [ ] Create Ubuntu 22.04 droplet on DO
- [ ] Install strongSwan
- [ ] Configure ipsec.conf and ipsec.secrets
- [ ] Open firewall ports (UDP 500, 4500)

### Step 2: Configure UniFi UDM Pro
- [ ] Create Site-to-Site VPN in UniFi Controller
- [ ] Match encryption settings
- [ ] Test connectivity to UCM (192.168.150.10)

### Step 3: Create DO Managed Services
- [ ] Create PostgreSQL managed database
- [ ] Create Redis managed cache
- [ ] Create DO Spaces bucket for audio

### Step 4: Create Production Dockerfiles
- [ ] frontend/Dockerfile (React + Nginx)
- [ ] backend/Dockerfile.api (FastAPI)
- [ ] backend/Dockerfile.worker (Celery)
- [ ] backend/Dockerfile.beat (Scheduler)
- [ ] backend/Dockerfile.dialer (Dialer engine)

### Step 5: Create app.yaml for App Platform
- [ ] Define all services
- [ ] Configure environment variables
- [ ] Set up health checks

### Step 6: Deploy Dialer Engine to VPN Droplet
- [ ] Build and push dialer image
- [ ] Run on VPN gateway droplet
- [ ] Verify SIP connectivity to UCM

### Step 7: Deploy App Platform Services
- [ ] Push code to GitHub
- [ ] Connect DO App Platform to repo
- [ ] Deploy and run migrations
- [ ] Test end-to-end

---

## Future SaaS Enhancements (Phase 2)

1. **Multi-tenancy** - Add organization/tenant model
2. **Auth system** - User registration, roles
3. **Billing** - Stripe integration, usage tracking
4. **Onboarding** - Self-service signup flow
