#!/bin/bash
# Download script for db-ip.com free IP geolocation database
# This script downloads the free IP to City Lite database in MMDB format
# Compatible with Plausible Analytics GeoIP2 integration
#
# Source: https://db-ip.com/db/
# License: Creative Commons Attribution License

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEOIP_DIR="${SCRIPT_DIR}/geoip"
CURRENT_YEAR=$(date +%Y)
CURRENT_MONTH=$(date +%m)

# Create geoip directory if it doesn't exist
mkdir -p "${GEOIP_DIR}"
cd "${GEOIP_DIR}"

echo "Downloading db-ip.com free IP geolocation database..."
echo ""

# Try multiple URL patterns - db-ip.com files are gzipped (.gz)
PREV_DATE=$(date -d "last month" +%Y-%m 2>/dev/null || date -v-1m +%Y-%m 2>/dev/null || echo "${CURRENT_YEAR}-12")

URL_PATTERNS=(
    "https://download.db-ip.com/free/dbip-city-lite-${CURRENT_YEAR}-${CURRENT_MONTH}.mmdb.gz"
    "https://download.db-ip.com/free/dbip-city-lite-${PREV_DATE}.mmdb.gz"
    "https://download.db-ip.com/free/dbip-city-lite-${CURRENT_YEAR}.mmdb.gz"
)

DOWNLOADED=0
TEMP_GZ_FILE="dbip-city-lite.mmdb.gz"

for URL in "${URL_PATTERNS[@]}"; do
    echo "Trying: ${URL}"
    if curl -L -f -s -o "${TEMP_GZ_FILE}" "${URL}" 2>/dev/null && [ -s "${TEMP_GZ_FILE}" ]; then
        # Verify it's a gzip file
        if file "${TEMP_GZ_FILE}" | grep -q "gzip\|compressed"; then
            echo "  ✓ Downloaded gzip file, extracting..."
            # Extract the gzip file (gunzip will remove the .gz file automatically)
            if gunzip -f "${TEMP_GZ_FILE}" 2>/dev/null; then
                # Verify the extracted file is a valid MMDB file
                if [ -f "dbip-city-lite.mmdb" ] && [ -s "dbip-city-lite.mmdb" ]; then
                    if file dbip-city-lite.mmdb | grep -q "MMDB\|MaxMind\|data"; then
                        echo "✓ Successfully downloaded and extracted db-ip.com database"
                        echo "  Location: ${GEOIP_DIR}/dbip-city-lite.mmdb"
                        ls -lh "${GEOIP_DIR}/dbip-city-lite.mmdb"
                        DOWNLOADED=1
                        break
                    else
                        rm -f dbip-city-lite.mmdb
                        echo "  ✗ Extracted file doesn't appear to be a valid MMDB file"
                    fi
                else
                    echo "  ✗ Failed to extract gzip file"
                fi
            else
                rm -f "${TEMP_GZ_FILE}"
                echo "  ✗ Failed to extract gzip file"
            fi
        else
            rm -f "${TEMP_GZ_FILE}"
            echo "  ✗ Downloaded file is not a gzip archive"
        fi
    else
        echo "  ✗ Not available"
    fi
done

# Clean up any leftover gz file
rm -f "${TEMP_GZ_FILE}"

if [ $DOWNLOADED -eq 0 ]; then
    echo ""
    echo "✗ Failed to download database automatically"
    echo ""
    echo "db-ip.com free databases require manual download:"
    echo ""
    echo "Option 1: Download via web browser"
    echo "  1. Visit: https://db-ip.com/db/download/ip-to-city-lite"
    echo "  2. Click 'Download' for the MMDB format"
    echo "  3. Save the file as: ${GEOIP_DIR}/dbip-city-lite.mmdb"
    echo ""
    echo "Option 2: Use wget/curl with the download page"
    echo "  The download page may require JavaScript or a form submission."
    echo "  Check the page source for the actual download link."
    echo ""
    echo "After downloading, restart Plausible:"
    echo "  cd $(dirname "${SCRIPT_DIR}") && docker-compose --env-file ../../config/.env restart plausible"
    exit 1
fi

echo ""
echo "Note: The free db-ip.com database is updated monthly."
echo "Run this script monthly to keep your geolocation data up to date."
echo ""
echo "To update automatically, add this to your crontab:"
echo "  0 0 1 * * $(realpath "${SCRIPT_DIR}/download-geoip.sh") && cd $(realpath "${SCRIPT_DIR}") && docker-compose --env-file ../../config/.env restart plausible"

