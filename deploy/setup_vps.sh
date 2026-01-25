#!/bin/bash

# ===========================================
# ASTRAEUS - VPS Setup Script
# ===========================================
# This script prepares a fresh Ubuntu/Debian VPS
# for running the ASTRAEUS bot
# ===========================================

set -e

echo "=========================================="
echo "ASTRAEUS - VPS Setup Script"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo)${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Updating system packages...${NC}"
apt-get update && apt-get upgrade -y

echo -e "${YELLOW}Step 2: Installing required packages...${NC}"
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common \
    git \
    ufw

echo -e "${YELLOW}Step 3: Installing Docker...${NC}"
# Remove old versions
apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

echo -e "${YELLOW}Step 4: Configuring firewall...${NC}"
# Allow SSH
ufw allow OpenSSH

# Allow webhook port (if using)
ufw allow 8443/tcp

# Enable firewall
ufw --force enable

echo -e "${YELLOW}Step 5: Creating application directory...${NC}"
APP_DIR="/opt/astraeus"
mkdir -p $APP_DIR
cd $APP_DIR

echo -e "${YELLOW}Step 6: Setting up non-root user for Docker...${NC}"
# Create astraeus user if doesn't exist
if ! id "astraeus" &>/dev/null; then
    useradd -m -s /bin/bash astraeus
    usermod -aG docker astraeus
fi

# Set ownership
chown -R astraeus:astraeus $APP_DIR

echo -e "${GREEN}=========================================="
echo "VPS Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Clone your repository to $APP_DIR"
echo "2. Copy .env.example to .env and configure"
echo "3. Run: docker compose up -d"
echo ""
echo "To check status: docker compose ps"
echo "To view logs: docker compose logs -f bot"
echo "==========================================${NC}"
