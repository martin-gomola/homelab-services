#!/bin/bash
# AFFiNE Update Script
# Safely updates AFFiNE to the latest version with automatic backup and rollback

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════${NC}"
echo -e "${BLUE}   AFFiNE Safe Update Script${NC}"
echo -e "${BLUE}═══════════════════════════════════════${NC}\n"

# Check if running on server
if [ ! -d "/srv/docker/affine" ]; then
    echo -e "${RED}Error: Not running on server. /srv/docker/affine not found.${NC}"
    exit 1
fi

# Get current version
CURRENT_VERSION=$(docker inspect affine_server --format='{{.Config.Image}}' 2>/dev/null | cut -d: -f2)
if [ -z "$CURRENT_VERSION" ]; then
    CURRENT_VERSION="unknown"
fi

echo -e "${YELLOW}Current version: ${CURRENT_VERSION}${NC}"
echo ""

# Prompt for target version
echo "Update options:"
echo "  1) Latest stable (recommended)"
echo "  2) Specific version (e.g., v0.25.6)"
echo "  3) Cancel"
echo ""
read -p "Select option [1-3]: " -r OPTION

case $OPTION in
    1)
        NEW_VERSION="stable"
        ;;
    2)
        read -p "Enter version (e.g., v0.25.6): " -r NEW_VERSION
        if [ -z "$NEW_VERSION" ]; then
            echo -e "${RED}No version specified. Exiting.${NC}"
            exit 1
        fi
        ;;
    3)
        echo -e "${YELLOW}Update cancelled${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid option. Exiting.${NC}"
        exit 1
        ;;
esac

echo -e "\n${YELLOW}Will update from ${CURRENT_VERSION} to ${NEW_VERSION}${NC}"
read -p "Continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${RED}Update cancelled${NC}"
    exit 0
fi

# Step 1: Create backup
echo -e "\n${BLUE}[1/6] Creating database backup...${NC}"
if [ -f "./backup-db.sh" ]; then
    ./backup-db.sh
    BACKUP_STATUS=$?
    if [ $BACKUP_STATUS -ne 0 ]; then
        echo -e "${RED}Backup failed. Aborting update.${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}Warning: backup-db.sh not found. Skipping backup.${NC}"
    read -p "Continue without backup? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        exit 0
    fi
fi

# Step 2: Update .env file
echo -e "\n${BLUE}[2/6] Updating version in .env...${NC}"
if grep -q "AFFINE_REVISION=" .env; then
    sed -i.bak "s/AFFINE_REVISION=.*/AFFINE_REVISION=\"${NEW_VERSION}\"/" .env
    echo -e "${GREEN}✓ Updated AFFINE_REVISION to ${NEW_VERSION}${NC}"
else
    echo -e "${YELLOW}Warning: AFFINE_REVISION not found in .env${NC}"
fi

# Step 3: Pull new images
echo -e "\n${BLUE}[3/6] Pulling new Docker images...${NC}"
docker-compose pull
if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to pull images. Restoring .env...${NC}"
    mv .env.bak .env 2>/dev/null || true
    exit 1
fi

# Step 4: Stop services
echo -e "\n${BLUE}[4/6] Stopping services...${NC}"
docker-compose down

# Step 5: Start services with new version
echo -e "\n${BLUE}[5/6] Starting services with new version...${NC}"
docker-compose up -d

# Step 6: Health check
echo -e "\n${BLUE}[6/6] Running health checks...${NC}"
echo -e "${YELLOW}Waiting for services to be healthy (60s timeout)...${NC}"

# Wait for services to be healthy
TIMEOUT=60
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    REDIS_HEALTH=$(docker inspect affine_redis --format='{{.State.Health.Status}}' 2>/dev/null || echo "unhealthy")
    POSTGRES_HEALTH=$(docker inspect affine_postgres --format='{{.State.Health.Status}}' 2>/dev/null || echo "unhealthy")
    SERVER_STATUS=$(docker inspect affine_server --format='{{.State.Status}}' 2>/dev/null || echo "stopped")

    if [ "$REDIS_HEALTH" = "healthy" ] && [ "$POSTGRES_HEALTH" = "healthy" ] && [ "$SERVER_STATUS" = "running" ]; then
        echo -e "${GREEN}✓ All services are healthy${NC}"
        break
    fi

    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo -n "."
done

echo ""

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo -e "${RED}✗ Health check timeout. Services may not be healthy.${NC}"
    echo -e "${YELLOW}Check logs with: docker-compose logs -f${NC}"

    read -p "Rollback to previous version? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${YELLOW}Rolling back...${NC}"
        mv .env.bak .env 2>/dev/null || true
        docker-compose down
        docker-compose up -d
        echo -e "${GREEN}Rollback complete${NC}"
    fi
    exit 1
fi

# Display current status
echo -e "\n${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}   Update Complete!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}\n"

UPDATED_VERSION=$(docker inspect affine_server --format='{{.Config.Image}}' | cut -d: -f2)
echo -e "Previous version: ${CURRENT_VERSION}"
echo -e "Current version:  ${UPDATED_VERSION}"
echo -e "\nService status:"
docker-compose ps

echo -e "\n${YELLOW}Recommended next steps:${NC}"
echo "1. Test the application at your configured domain"
echo "2. Check logs: docker-compose logs -f affine_server"
echo "3. Monitor for any issues"
echo ""
echo -e "${GREEN}Backup saved in: /srv/backups/affine/postgres/${NC}"

# Clean up old backup of .env
rm -f .env.bak 2>/dev/null || true
