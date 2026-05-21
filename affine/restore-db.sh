#!/bin/bash
# AFFiNE PostgreSQL Restore Script
# This script restores the AFFiNE database from a backup

set -e

# Configuration
BACKUP_DIR="/srv/backups/affine/postgres"
CONTAINER_NAME="affine_postgres"
DB_NAME="affinedb"
DB_USER="affine"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AFFiNE Database Restore ===${NC}"

# Check if backup file is provided
if [ -z "$1" ]; then
    echo -e "${YELLOW}Available backups:${NC}"
    ls -lh "${BACKUP_DIR}"/affine_backup_*.sql.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    echo ""
    echo -e "${RED}Usage: $0 <backup_file>${NC}"
    echo -e "Example: $0 affine_backup_20240115_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Check if backup file exists
if [ ! -f "${BACKUP_PATH}" ]; then
    echo -e "${RED}Error: Backup file not found: ${BACKUP_PATH}${NC}"
    exit 1
fi

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}Error: Container ${CONTAINER_NAME} is not running${NC}"
    exit 1
fi

# Warning and confirmation
echo -e "${YELLOW}WARNING: This will replace the current database!${NC}"
echo "Database: ${DB_NAME}"
echo "Backup file: ${BACKUP_FILE}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${RED}Restore cancelled${NC}"
    exit 0
fi

# Create a backup of current database before restore
echo -e "${YELLOW}Creating safety backup of current database...${NC}"
SAFETY_BACKUP="affine_pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
docker exec -t "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${BACKUP_DIR}/${SAFETY_BACKUP}"
echo -e "${GREEN}✓ Safety backup created: ${SAFETY_BACKUP}${NC}"

# Stop AFFiNE services
echo -e "${YELLOW}Stopping AFFiNE services...${NC}"
docker stop affine_server affine_migration_job 2>/dev/null || true

# Restore database
echo -e "${YELLOW}Restoring database...${NC}"
gunzip < "${BACKUP_PATH}" | docker exec -i "${CONTAINER_NAME}" psql -U "${DB_USER}" -d "${DB_NAME}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Database restored successfully${NC}"
else
    echo -e "${RED}✗ Restore failed${NC}"
    exit 1
fi

# Restart services
echo -e "${YELLOW}Restarting AFFiNE services...${NC}"
docker start affine_server

echo -e "\n${GREEN}=== Restore Complete ===${NC}"
echo -e "Safety backup saved as: ${SAFETY_BACKUP}"
