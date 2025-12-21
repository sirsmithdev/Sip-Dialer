# SIP-Dialer Deployment Guide

This guide covers deploying SIP-Dialer as a SaaS application on Digital Ocean.

## Architecture Overview

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

## Deployment Steps

### Step 1: Create VPN Gateway Droplet

1. Create Ubuntu 22.04 droplet ($6/mo is sufficient)
2. Note the droplet's public IP
3. SSH into droplet and run setup:

```bash
# Clone repo or copy vpn folder
cd /opt
git clone https://github.com/YOUR_USERNAME/sip-dialer.git
cd sip-dialer/deploy/vpn

# Run setup script
sudo bash setup.sh
```

### Step 2: Configure IPsec VPN

1. Edit `/etc/ipsec.conf`:
   - Replace `<YOUR_HOME_PUBLIC_IP>` with your static IP
   - Replace `<YOUR_LOCAL_SUBNET>` with `192.168.150.0/24`

2. Edit `/etc/ipsec.secrets`:
   - Replace IPs
   - Generate and set PSK: `openssl rand -base64 32`

3. Start strongSwan:
```bash
sudo systemctl enable strongswan-starter
sudo systemctl restart strongswan-starter
sudo ipsec restart
```

### Step 3: Configure UniFi UDM Pro

1. Go to Settings → VPN → Site-to-Site VPN
2. Create new Manual IPsec VPN:
   - **VPN Type**: Site-to-Site
   - **Remote Gateway IP**: DO Droplet public IP
   - **Remote Networks**: `10.10.10.0/24`
   - **Pre-shared Key**: Same as ipsec.secrets
   - **IKE Version**: IKEv2
   - **Encryption**: AES-256
   - **Hash**: SHA-256
   - **DH Group**: 14 (modp2048)

### Step 4: Verify VPN Connection

```bash
# On DO Droplet
sudo ipsec statusall

# Should show ESTABLISHED
# Test connectivity to UCM
ping 192.168.150.10
```

### Step 5: Create DO Managed Services

```bash
# PostgreSQL
doctl databases create sip-dialer-db \
  --engine pg \
  --version 15 \
  --size db-s-1vcpu-1gb \
  --region nyc1

# Redis
doctl databases create sip-dialer-redis \
  --engine redis \
  --size db-s-1vcpu-1gb \
  --region nyc1

# Spaces bucket
doctl spaces create sip-dialer-audio --region nyc3
```

### Step 6: Deploy App Platform

1. Push code to GitHub

2. Update `app.yaml`:
   - Replace `YOUR_GITHUB_USERNAME` with your username

3. Deploy:
```bash
doctl apps create --spec app.yaml
```

4. Set secrets in DO Console:
   - `JWT_SECRET_KEY`
   - `ENCRYPTION_KEY`
   - `S3_ACCESS_KEY`
   - `S3_SECRET_KEY`

### Step 7: Deploy Dialer Engine

On the VPN Gateway Droplet:

```bash
cd /opt/sip-dialer/deploy/vpn

# Configure environment
cp .env.example .env
nano .env  # Fill in your values

# Start dialer
docker compose -f docker-compose.dialer.yml up -d

# Check logs
docker compose -f docker-compose.dialer.yml logs -f
```

### Step 8: Run Database Migrations

```bash
# SSH to API container or run locally with production DB
alembic upgrade head
```

## Estimated Monthly Costs

| Service | Cost |
|---------|------|
| App Platform (3 services) | ~$17/mo |
| Managed PostgreSQL | $15/mo |
| Managed Redis | $15/mo |
| VPN Gateway Droplet | $6/mo |
| DO Spaces (25GB) | $5/mo |
| **Total** | **~$58/mo** |

## Troubleshooting

### VPN not connecting

```bash
# Check strongSwan logs
journalctl -u strongswan-starter -f

# Verify IKE traffic
tcpdump -i eth0 udp port 500 or udp port 4500

# Restart VPN
sudo ipsec restart
```

### Can't reach UCM after VPN is up

```bash
# Check routing
ip route

# Verify tunnel is ESTABLISHED
sudo ipsec status

# Check for NAT issues
sudo iptables -t nat -L
```

### Dialer not registering with UCM

```bash
# Check dialer logs
docker compose -f docker-compose.dialer.yml logs -f

# Verify SIP connectivity
nc -zvu 192.168.150.10 5060

# Check PJSUA2 is working
docker exec sip-dialer-engine python -c "import pjsua2; print('OK')"
```

## Security Notes

1. **IPsec PSK**: Use a strong, random key (32+ characters)
2. **Database**: Use SSL connections (enabled by default on DO)
3. **Secrets**: Never commit `.env` files to git
4. **Firewall**: Keep UFW enabled on droplet
5. **Updates**: Regularly update droplet packages
