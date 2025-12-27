#!/bin/bash
# =============================================================================
# SIP Dialer - Droplet Deployment Script
# =============================================================================
# This script sets up a fresh Ubuntu Droplet for running SIP Dialer
#
# Usage:
#   1. Create a Droplet (Ubuntu 22.04, 4GB RAM recommended)
#   2. SSH into the Droplet
#   3. Run: curl -sSL https://raw.githubusercontent.com/sirsmithdev/Sip-Dialer/deploy/digitalocean/deploy/droplet/deploy.sh | bash
#   Or clone and run locally:
#   4. git clone https://github.com/sirsmithdev/Sip-Dialer.git
#   5. cd Sip-Dialer/deploy/droplet
#   6. chmod +x deploy.sh && ./deploy.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# STEP 1: System Update & Dependencies
# =============================================================================
log_info "Updating system packages..."
apt-get update && apt-get upgrade -y

log_info "Installing dependencies..."
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    ufw

# =============================================================================
# STEP 2: Install Docker
# =============================================================================
if ! command -v docker &> /dev/null; then
    log_info "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh

    # Add current user to docker group
    usermod -aG docker $USER

    # Enable Docker service
    systemctl enable docker
    systemctl start docker
else
    log_info "Docker already installed"
fi

# =============================================================================
# STEP 3: Install Docker Compose
# =============================================================================
if ! command -v docker-compose &> /dev/null; then
    log_info "Installing Docker Compose..."
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
    curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
else
    log_info "Docker Compose already installed"
fi

# =============================================================================
# STEP 4: Configure Firewall (UFW)
# =============================================================================
log_info "Configuring firewall..."

# Reset UFW to defaults
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# SSH (important - don't lock yourself out!)
ufw allow 22/tcp

# HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# SIP Signaling
ufw allow 5060/udp  # SIP UDP
ufw allow 5060/tcp  # SIP TCP
ufw allow 5061/tcp  # SIP TLS

# RTP Media (adjust range as needed)
ufw allow 10000:20000/udp

# Enable firewall
ufw --force enable

log_info "Firewall configured with SIP ports open"

# =============================================================================
# STEP 5: Clone Repository
# =============================================================================
DEPLOY_DIR="/opt/sip-dialer"

if [ -d "$DEPLOY_DIR" ]; then
    log_info "Updating existing deployment..."
    cd $DEPLOY_DIR
    git pull origin deploy/digitalocean
else
    log_info "Cloning repository..."
    git clone -b deploy/digitalocean https://github.com/sirsmithdev/Sip-Dialer.git $DEPLOY_DIR
    cd $DEPLOY_DIR
fi

# =============================================================================
# STEP 6: Setup Environment
# =============================================================================
cd $DEPLOY_DIR/deploy/droplet

if [ ! -f .env ]; then
    log_warn ".env file not found!"
    log_info "Creating .env from template..."
    cp .env.example .env
    log_warn "IMPORTANT: Edit .env file with your configuration before continuing!"
    log_warn "Run: nano $DEPLOY_DIR/deploy/droplet/.env"
    log_info ""
    log_info "After editing .env, run: cd $DEPLOY_DIR/deploy/droplet && docker-compose -f docker-compose.droplet.yml up -d"
    exit 0
fi

# =============================================================================
# STEP 7: Build and Deploy
# =============================================================================
log_info "Building Docker images..."
docker-compose -f docker-compose.droplet.yml build

log_info "Starting services..."
docker-compose -f docker-compose.droplet.yml up -d

# =============================================================================
# STEP 8: Create systemd service for auto-restart
# =============================================================================
log_info "Creating systemd service..."
cat > /etc/systemd/system/sip-dialer.service << 'EOF'
[Unit]
Description=SIP Dialer Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/sip-dialer/deploy/droplet
ExecStart=/usr/local/bin/docker-compose -f docker-compose.droplet.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.droplet.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable sip-dialer

# =============================================================================
# STEP 9: Show Status
# =============================================================================
log_info "Deployment complete!"
echo ""
echo "=============================================="
echo "  SIP Dialer Droplet Deployment Complete"
echo "=============================================="
echo ""
echo "Services running:"
docker-compose -f docker-compose.droplet.yml ps
echo ""
echo "Droplet IP: $(curl -s ifconfig.me)"
echo ""
echo "Next steps:"
echo "  1. Point your domain DNS to this IP"
echo "  2. Update UCM SIP server to this IP"
echo "  3. Check logs: docker-compose -f docker-compose.droplet.yml logs -f"
echo ""
echo "Useful commands:"
echo "  View logs:    docker-compose -f docker-compose.droplet.yml logs -f"
echo "  Restart:      docker-compose -f docker-compose.droplet.yml restart"
echo "  Stop:         docker-compose -f docker-compose.droplet.yml down"
echo "  Update:       git pull && docker-compose -f docker-compose.droplet.yml up -d --build"
echo ""
