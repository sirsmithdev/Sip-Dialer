# SIP Dialer - Droplet Deployment

Deploy the SIP Dialer to a DigitalOcean Droplet with full SIP inbound/outbound support.

## Why Droplet over App Platform?

| Feature | App Platform | Droplet |
|---------|-------------|---------|
| HTTP Ingress | Yes | Yes |
| SIP/UDP Ingress | **No** | **Yes** |
| Inbound Calls | **No** | **Yes** |
| Outbound Calls | Yes | Yes |
| Static IP | Egress only | **Full** |
| Cost | ~$50/mo | ~$48/mo |

## Prerequisites

- DigitalOcean account
- Domain name (for SSL)
- Existing managed services:
  - PostgreSQL: `sip-dialer-db`
  - Redis/Valkey: `sip-dialer-cache`
  - Spaces: `sip-dialer-audio`

## Quick Start

### Step 1: Create Droplet

1. Go to [DigitalOcean Droplets](https://cloud.digitalocean.com/droplets/new)
2. Choose:
   - **Region**: NYC1 (same as managed services)
   - **Image**: Ubuntu 22.04 (LTS) x64
   - **Size**: Basic → Regular → **$48/mo** (4 vCPU / 8GB RAM)
   - **Authentication**: SSH key (recommended)
   - **Hostname**: `sip-dialer`
   - **Tags**: `sip-dialer`, `production`

3. Click **Create Droplet**
4. Note the IP address

### Step 2: Configure DNS

Point your domain to the Droplet IP:
```
A    sip-dialer.yourdomain.com    →    <DROPLET_IP>
```

### Step 3: SSH into Droplet

```bash
ssh root@<DROPLET_IP>
```

### Step 4: Run Deployment Script

```bash
# Clone repository
git clone -b deploy/digitalocean https://github.com/sirsmithdev/Sip-Dialer.git /opt/sip-dialer

# Navigate to deploy directory
cd /opt/sip-dialer/deploy/droplet

# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

The script will:
- Install Docker & Docker Compose
- Configure UFW firewall (SIP ports)
- Set up systemd service for auto-restart
- Create `.env` file template

### Step 5: Configure Environment

Edit the `.env` file with your actual values:

```bash
nano /opt/sip-dialer/deploy/droplet/.env
```

Fill in:
```env
# Domain for SSL
DOMAIN=sip-dialer.yourdomain.com

# PostgreSQL (from DO Managed Database)
DATABASE_URL=postgresql+asyncpg://doadmin:YOUR_DB_PASSWORD@your-db-cluster.db.ondigitalocean.com:25060/defaultdb?sslmode=require

# Redis/Valkey (from DO Managed Database)
REDIS_URL=rediss://default:YOUR_REDIS_PASSWORD@your-redis-cluster.db.ondigitalocean.com:25061

# Spaces (from DO Spaces)
S3_ENDPOINT=nyc3.digitaloceanspaces.com
S3_ACCESS_KEY=YOUR_SPACES_ACCESS_KEY
S3_SECRET_KEY=YOUR_SPACES_SECRET_KEY
S3_BUCKET=sip-dialer-audio
S3_BUCKET_RECORDINGS=sip-dialer-recordings
S3_REGION=nyc3

# Security (generate new ones)
JWT_SECRET_KEY=<generate: openssl rand -base64 32>
ENCRYPTION_KEY=YOUR_FERNET_ENCRYPTION_KEY

# OpenAI
OPENAI_API_KEY=sk-...
```

### Step 6: Start Services

```bash
cd /opt/sip-dialer/deploy/droplet
docker-compose -f docker-compose.droplet.yml up -d
```

### Step 7: Update UCM Configuration

Update your UCM/PBX SIP settings to point to the Droplet:
```
SIP Server: <DROPLET_IP>
SIP Port: 5061
Transport: TLS
```

### Step 8: Verify Deployment

```bash
# Check all services are running
docker-compose -f docker-compose.droplet.yml ps

# Check dialer-engine logs
docker logs sip-dialer-engine -f

# Verify SIP registration
# Look for: "SIP registration successful"
```

## Firewall Ports

The deployment script automatically configures UFW:

| Port | Protocol | Purpose |
|------|----------|---------|
| 22 | TCP | SSH |
| 80 | TCP | HTTP (redirect to HTTPS) |
| 443 | TCP | HTTPS |
| 5060 | UDP/TCP | SIP Signaling |
| 5061 | TCP | SIP TLS |
| 10000-20000 | UDP | RTP Media |

## Management Commands

```bash
# View logs
docker-compose -f docker-compose.droplet.yml logs -f

# View specific service logs
docker logs sip-dialer-engine -f
docker logs sip-dialer-api -f

# Restart all services
docker-compose -f docker-compose.droplet.yml restart

# Restart specific service
docker-compose -f docker-compose.droplet.yml restart dialer-engine

# Stop all services
docker-compose -f docker-compose.droplet.yml down

# Update to latest code
cd /opt/sip-dialer
git pull origin deploy/digitalocean
docker-compose -f deploy/droplet/docker-compose.droplet.yml up -d --build

# View container status
docker-compose -f docker-compose.droplet.yml ps
```

## Monitoring

### Health Check
```bash
curl https://sip-dialer.yourdomain.com/api/v1/health
```

### SIP Status
```bash
# Via Redis
docker exec -it sip-dialer-engine redis-cli -u $REDIS_URL GET dialer:sip_status
```

## Troubleshooting

### SIP Registration Fails
1. Check firewall allows outbound to UCM
2. Verify SIP credentials in database
3. Check dialer-engine logs: `docker logs sip-dialer-engine`

### SSL Certificate Issues
1. Caddy auto-provisions Let's Encrypt certificates
2. Ensure domain DNS is pointing to Droplet IP
3. Check Caddy logs: `docker logs sip-dialer-caddy`

### Database Connection Issues
1. Verify DATABASE_URL in .env
2. Check if Droplet IP is in database trusted sources
3. Test: `docker exec -it sip-dialer-api python -c "from app.db import engine; print('OK')"`

## Cleanup (Optional)

To delete the old App Platform deployment after migration:
```bash
doctl apps delete <APP_ID>
```

Or via the [DO Console](https://cloud.digitalocean.com/apps).

## Cost Comparison

| Resource | App Platform | Droplet |
|----------|-------------|---------|
| Compute | ~$37/mo | $48/mo |
| Managed PostgreSQL | $15/mo | $15/mo |
| Managed Redis | $15/mo | $15/mo |
| Spaces | ~$5/mo | ~$5/mo |
| **Total** | ~$72/mo | ~$83/mo |

Note: Droplet cost can be reduced to $24/mo (2 vCPU/4GB) for lighter workloads.
