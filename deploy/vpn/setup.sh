#!/bin/bash
# =============================================================================
# VPN Gateway Setup Script for Digital Ocean Droplet
# =============================================================================
# This script sets up a Digital Ocean droplet as a VPN gateway to connect
# to your on-premise UniFi UDM Pro and access the Grandstream UCM6302 PBX.
#
# Usage:
#   1. Create Ubuntu 22.04 droplet on Digital Ocean
#   2. SSH into the droplet
#   3. Run: bash setup.sh
#   4. Edit /etc/ipsec.conf and /etc/ipsec.secrets with your values
#   5. Configure matching VPN on UniFi UDM Pro
# =============================================================================

set -e

echo "==================================="
echo "VPN Gateway Setup for SIP-Dialer"
echo "==================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo bash setup.sh)"
    exit 1
fi

# Get droplet public IP
DROPLET_IP=$(curl -s http://169.254.169.254/metadata/v1/interfaces/public/0/ipv4/address 2>/dev/null || hostname -I | awk '{print $1}')
echo "Detected droplet IP: $DROPLET_IP"

# =============================================================================
# Install Dependencies
# =============================================================================
echo ""
echo "Installing strongSwan and Docker..."
apt update
apt install -y strongswan strongswan-pki libcharon-extra-plugins

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    apt install -y docker-compose-plugin
fi

# =============================================================================
# Enable IP Forwarding
# =============================================================================
echo ""
echo "Enabling IP forwarding..."
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
echo "net.ipv4.conf.all.accept_redirects=0" >> /etc/sysctl.conf
echo "net.ipv4.conf.all.send_redirects=0" >> /etc/sysctl.conf
sysctl -p

# =============================================================================
# Configure Firewall
# =============================================================================
echo ""
echo "Configuring firewall..."

# Allow IPsec traffic
ufw allow 500/udp comment "IKE"
ufw allow 4500/udp comment "NAT-T"

# Allow Docker and internal traffic
ufw allow from 10.10.10.0/24 comment "VPN subnet"

# Enable firewall if not already enabled
ufw --force enable

# =============================================================================
# Copy Configuration Templates
# =============================================================================
echo ""
echo "Copying strongSwan configuration templates..."

# Backup existing configs
if [ -f /etc/ipsec.conf ]; then
    mv /etc/ipsec.conf /etc/ipsec.conf.backup
fi
if [ -f /etc/ipsec.secrets ]; then
    mv /etc/ipsec.secrets /etc/ipsec.secrets.backup
fi

# Copy templates (assumes script is run from deploy/vpn directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/ipsec.conf" /etc/ipsec.conf
cp "$SCRIPT_DIR/ipsec.secrets" /etc/ipsec.secrets

# Set proper permissions
chmod 600 /etc/ipsec.secrets

# Replace DO_DROPLET_PUBLIC_IP with actual IP
sed -i "s/<DO_DROPLET_PUBLIC_IP>/$DROPLET_IP/g" /etc/ipsec.conf
sed -i "s/<DO_DROPLET_PUBLIC_IP>/$DROPLET_IP/g" /etc/ipsec.secrets

# =============================================================================
# Configure Virtual IP
# =============================================================================
echo ""
echo "Configuring virtual IP for VPN subnet..."

# Add virtual IP to the droplet
ip addr add 10.10.10.1/24 dev eth0 2>/dev/null || true

# Make it persistent
cat > /etc/netplan/99-vpn.yaml << EOF
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 10.10.10.1/24
EOF
netplan apply 2>/dev/null || true

# =============================================================================
# Create Dialer Directory
# =============================================================================
echo ""
echo "Creating dialer directory..."
mkdir -p /opt/sip-dialer
mkdir -p /var/lib/autodialer/audio

# =============================================================================
# Print Next Steps
# =============================================================================
echo ""
echo "==================================="
echo "Setup Complete!"
echo "==================================="
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Edit /etc/ipsec.conf and replace:"
echo "   - <YOUR_HOME_PUBLIC_IP> with your static public IP"
echo "   - <YOUR_LOCAL_SUBNET> with your local network (e.g., 192.168.150.0/24)"
echo ""
echo "2. Edit /etc/ipsec.secrets and replace:"
echo "   - <YOUR_HOME_PUBLIC_IP> with your static public IP"
echo "   - REPLACE_WITH_A_STRONG_32_CHAR_RANDOM_KEY with a secure PSK"
echo "   - Generate a PSK with: openssl rand -base64 32"
echo ""
echo "3. Configure UniFi UDM Pro:"
echo "   - Settings → VPN → Site-to-Site VPN"
echo "   - Remote Gateway: $DROPLET_IP"
echo "   - Remote Networks: 10.10.10.0/24"
echo "   - Pre-shared Key: (same as ipsec.secrets)"
echo "   - IKEv2, AES-256, SHA-256, DH Group 14"
echo ""
echo "4. Start strongSwan:"
echo "   systemctl enable strongswan-starter"
echo "   systemctl restart strongswan-starter"
echo "   ipsec restart"
echo ""
echo "5. Verify VPN connection:"
echo "   ipsec statusall"
echo "   ping <UCM_IP>  # e.g., ping 192.168.150.10"
echo ""
echo "6. Deploy dialer engine:"
echo "   Copy docker-compose.dialer.yml to /opt/sip-dialer/"
echo "   cd /opt/sip-dialer && docker compose up -d"
echo ""
