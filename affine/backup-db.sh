#!/bin/bash
# AFFiNE PostgreSQL Backup Script
# This script creates backups of the AFFiNE database

set -e

# Configuration
BACKUP_DIR="/srv/backups/affine/postgres"
CONTAINER_NAME="affine_postgres"
DB_NAME="affinedb"
DB_USER="affine"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="affine_backup_${TIMESTAMP}.sql.gz"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AFFiNE Database Backup ===${NC}"
echo "Timestamp: $(date)"
echo "Database: ${DB_NAME}"
echo "Container: ${CONTAINER_NAME}"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}Error: Container ${CONTAINER_NAME} is not running${NC}"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Create backup
echo -e "${YELLOW}Creating backup...${NC}"
docker exec -t "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
    echo -e "${GREEN}✓ Backup created successfully: ${BACKUP_FILE} (${BACKUP_SIZE})${NC}"
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

# Remove old backups
echo -e "${YELLOW}Cleaning up old backups (older than ${RETENTION_DAYS} days)...${NC}"
find "${BACKUP_DIR}" -name "affine_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete

REMAINING_BACKUPS=$(find "${BACKUP_DIR}" -name "affine_backup_*.sql.gz" -type f | wc -l)
echo -e "${GREEN}✓ Cleanup complete. Total backups: ${REMAINING_BACKUPS}${NC}"

# Display recent backups
echo -e "\n${GREEN}Recent backups:${NC}"
ls -lh "${BACKUP_DIR}"/affine_backup_*.sql.gz 2>/dev/null | tail -5 | awk '{print "  " $9 " (" $5 ")"}'

echo -e "\n${GREEN}=== Backup Complete ===${NC}"
