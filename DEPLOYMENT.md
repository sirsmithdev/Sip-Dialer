# SIP Auto-Dialer - Windows Server Deployment Guide

This guide walks you through deploying the SIP Auto-Dialer on a Windows Server using Docker.

## Prerequisites

### 1. Windows Server Requirements

- **OS**: Windows Server 2019 or later (with Containers feature)
- **RAM**: Minimum 8GB, recommended 16GB+
- **Storage**: Minimum 50GB free space
- **CPU**: 4+ cores recommended

### 2. Install Docker Desktop for Windows

1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop/
2. Run the installer
3. During installation, ensure **WSL 2** backend is selected (recommended)
4. Restart your computer when prompted
5. After restart, open Docker Desktop and complete the setup

**For Windows Server (without Docker Desktop):**
```powershell
# Install Docker EE on Windows Server
Install-Module -Name DockerMsftProvider -Repository PSGallery -Force
Install-Package -Name docker -ProviderName DockerMsftProvider -Force
Restart-Computer
```

### 3. Verify Docker Installation

Open Command Prompt or PowerShell and run:
```cmd
docker --version
docker-compose --version
```

## Quick Start

### 1. Clone or Copy the Project

Copy the entire `sip-autodialer` folder to your Windows Server, for example:
```
C:\Projects\sip-autodialer
```

### 2. Navigate to Project Directory

```cmd
cd C:\Projects\sip-autodialer
```

### 3. Configure Environment

Copy the example environment file:
```cmd
copy .env.example .env
```

Edit `.env` with your settings (see Configuration section below).

### 4. Deploy Using the Batch Script

For first-time setup:
```cmd
deploy-windows.bat init
```

This will:
- Build all Docker images
- Create necessary volumes
- Start all services
- Run database migrations

## Configuration

### Essential `.env` Settings

Edit the `.env` file with your specific configuration:

```env
# ============================================================
# REQUIRED - Change these for production!
# ============================================================

# Database
POSTGRES_USER=sipdialer
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE
POSTGRES_DB=sipdialer

# Security - Generate a secure key!
# PowerShell: [Convert]::ToBase64String((1..32|%{Get-Random -Max 256}))
SECRET_KEY=your-secure-secret-key-min-32-chars

# Admin User
ADMIN_EMAIL=admin@yourcompany.com
ADMIN_PASSWORD=YourSecurePassword123!

# ============================================================
# Asterisk/SIP Configuration
# ============================================================

# Your Asterisk server connection
AMI_HOST=your-asterisk-server.local
AMI_PORT=5038
AMI_USERNAME=dialer
AMI_PASSWORD=your-ami-password

# SIP Trunk settings
SIP_PROXY=sip.yourprovider.com
SIP_USERNAME=your-sip-username
SIP_PASSWORD=your-sip-password

# ============================================================
# MinIO (Object Storage)
# ============================================================
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=YourMinioPassword123!

# ============================================================
# Optional - Defaults usually work
# ============================================================

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# API Settings
API_HOST=0.0.0.0
API_PORT=8000
```

### Generating a Secure Secret Key

In PowerShell:
```powershell
[Convert]::ToBase64String((1..32|ForEach-Object{Get-Random -Maximum 256}))
```

Or in Command Prompt with Python:
```cmd
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Deployment Commands

The `deploy-windows.bat` script provides these commands:

| Command | Description |
|---------|-------------|
| `deploy-windows.bat init` | First-time setup (build, create volumes, start, migrate) |
| `deploy-windows.bat build` | Build all Docker images |
| `deploy-windows.bat start` | Start all services |
| `deploy-windows.bat stop` | Stop all services |
| `deploy-windows.bat restart` | Restart all services |
| `deploy-windows.bat logs` | View all logs |
| `deploy-windows.bat logs api-gateway` | View specific service logs |
| `deploy-windows.bat status` | Show service status |
| `deploy-windows.bat prod` | Start in production mode |
| `deploy-windows.bat clean` | Remove all containers and data (DESTRUCTIVE!) |

## Services and Ports

After deployment, these services are available:

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Web application |
| API | http://localhost:8000 | REST API |
| API Docs | http://localhost:8000/docs | Swagger documentation |
| Flower | http://localhost:5555 | Celery task monitor |
| MinIO Console | http://localhost:9001 | Object storage admin |

## Production Deployment

For production environments, use the production compose file:

```cmd
deploy-windows.bat prod
```

Or manually:
```cmd
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Production Checklist

- [ ] Change all default passwords in `.env`
- [ ] Generate a secure `SECRET_KEY`
- [ ] Configure proper Asterisk AMI credentials
- [ ] Set up SIP trunk credentials
- [ ] Configure Windows Firewall rules
- [ ] Set up SSL/TLS certificates (see below)
- [ ] Configure backup strategy
- [ ] Set up monitoring

### SSL/TLS Configuration

For production, you should configure SSL. Options:

1. **Using a reverse proxy (recommended)**:
   - Install Nginx or IIS as a reverse proxy
   - Configure SSL certificates there
   - Proxy requests to Docker containers

2. **Using Traefik** (add to docker-compose):
   ```yaml
   traefik:
     image: traefik:v2.10
     command:
       - "--providers.docker=true"
       - "--entrypoints.websecure.address=:443"
       - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
       - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
     ports:
       - "443:443"
     volumes:
       - /var/run/docker.sock:/var/run/docker.sock
   ```

## Windows Firewall Configuration

Allow these ports through Windows Firewall:

```powershell
# Web traffic
New-NetFirewallRule -DisplayName "SIP Dialer - Frontend" -Direction Inbound -Port 3000 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "SIP Dialer - API" -Direction Inbound -Port 8000 -Protocol TCP -Action Allow

# Optional monitoring
New-NetFirewallRule -DisplayName "SIP Dialer - Flower" -Direction Inbound -Port 5555 -Protocol TCP -Action Allow

# AGI Server (if Asterisk connects to this server)
New-NetFirewallRule -DisplayName "SIP Dialer - AGI" -Direction Inbound -Port 4573 -Protocol TCP -Action Allow
```

## Connecting to Asterisk

### Option 1: Asterisk on Same Network

If your Asterisk server is on the same network:

1. Ensure Asterisk AMI is enabled in `/etc/asterisk/manager.conf`:
   ```ini
   [general]
   enabled = yes
   port = 5038
   bindaddr = 0.0.0.0

   [dialer]
   secret = your-ami-password
   deny = 0.0.0.0/0.0.0.0
   permit = YOUR_WINDOWS_SERVER_IP/255.255.255.255
   read = all
   write = all
   ```

2. Update `.env` with Asterisk IP:
   ```env
   AMI_HOST=192.168.1.100
   ```

### Option 2: Asterisk in Docker

You can run Asterisk in the same Docker environment. Add to `docker-compose.yml`:

```yaml
asterisk:
  image: andrius/asterisk:alpine-20
  ports:
    - "5060:5060/udp"
    - "5060:5060/tcp"
    - "5038:5038"
    - "10000-10100:10000-10100/udp"
  volumes:
    - ./asterisk/config:/etc/asterisk
    - ./asterisk/sounds:/var/lib/asterisk/sounds/custom
  networks:
    - backend_net
```

## Backup and Recovery

### Backup Database

```cmd
docker-compose exec postgresql pg_dump -U sipdialer sipdialer > backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%.sql
```

### Restore Database

```cmd
type backup_20240101.sql | docker-compose exec -T postgresql psql -U sipdialer sipdialer
```

### Backup Volumes

```cmd
docker run --rm -v sip-autodialer_postgres_data:/data -v %cd%:/backup alpine tar czf /backup/postgres_backup.tar.gz /data
docker run --rm -v sip-autodialer_minio_data:/data -v %cd%:/backup alpine tar czf /backup/minio_backup.tar.gz /data
```

## Troubleshooting

### Services Won't Start

1. Check Docker is running:
   ```cmd
   docker info
   ```

2. Check for port conflicts:
   ```cmd
   netstat -an | findstr "3000 8000 5432 6379"
   ```

3. View service logs:
   ```cmd
   deploy-windows.bat logs
   ```

### Database Connection Issues

1. Check PostgreSQL is running:
   ```cmd
   docker-compose ps postgresql
   ```

2. Test database connection:
   ```cmd
   docker-compose exec postgresql psql -U sipdialer -c "SELECT 1"
   ```

### API Not Responding

1. Check API logs:
   ```cmd
   deploy-windows.bat logs api-gateway
   ```

2. Verify API is running:
   ```cmd
   curl http://localhost:8000/health
   ```

### Docker Resource Issues

If containers are crashing due to memory:

1. Increase Docker Desktop memory allocation:
   - Open Docker Desktop > Settings > Resources
   - Increase Memory to 8GB+

2. Or reduce resource limits in `docker-compose.prod.yml`

### Windows-Specific Issues

**Long path issues:**
```cmd
git config --system core.longpaths true
```

**Line ending issues:**
```cmd
git config --global core.autocrlf false
```

**WSL 2 not working:**
1. Enable WSL: `wsl --install`
2. Restart computer
3. Set WSL 2 as default: `wsl --set-default-version 2`

## Updating

To update to a new version:

```cmd
# Pull latest code
git pull

# Rebuild and restart
deploy-windows.bat stop
deploy-windows.bat build
deploy-windows.bat start

# Run any new migrations
docker-compose exec api-gateway alembic upgrade head
```

## Support

For issues and questions:
- Check the logs: `deploy-windows.bat logs`
- Review this documentation
- Check Docker Desktop logs
- Ensure all prerequisites are met
