#!/bin/bash
# Manual workflow test script for FHIR ingestion
# This script tests the complete flow from API submission to storage verification

set -e

echo "========================================"
echo "   FHIR Ingestion Workflow Test"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Start services
echo -e "${BLUE}[1/7]${NC} Starting services..."
docker compose up -d
echo "Waiting for services to be ready..."
sleep 8

# Step 2: Check health
echo ""
echo -e "${BLUE}[2/7]${NC} Checking API health..."
HEALTH=$(curl -s http://localhost:8000/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} API is healthy"
else
    echo "✗ API health check failed"
    exit 1
fi

# Step 3: Send bundle
echo ""
echo -e "${BLUE}[3/7]${NC} Sending FHIR bundle..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/fhir/ingest" \
     -H "Content-Type: application/json" \
     -d @tests/examples/fhir_bundles/sample_ch_elm_bundle.json)

echo "$RESPONSE" | python3 -m json.tool
BUNDLE_ID=$(echo "$RESPONSE" | grep -o '"bundle_id":"[^"]*' | cut -d'"' -f4)

if [ -z "$BUNDLE_ID" ]; then
    echo "✗ Failed to get bundle_id from response"
    exit 1
fi

echo -e "${GREEN}✓${NC} Bundle submitted with ID: ${YELLOW}${BUNDLE_ID}${NC}"

# Step 4: Wait for processing
echo ""
echo -e "${BLUE}[4/7]${NC} Waiting for processing..."
sleep 3

# Step 5: Check MinIO
echo ""
echo -e "${BLUE}[5/7]${NC} Checking MinIO storage..."
MINIO_CHECK=$(docker compose exec -T fhir-api python3 << 'EOF'
from minio import Minio
from config import get_minio_config

config = get_minio_config()
client = Minio(
    endpoint=config["endpoint"],
    access_key=config["access_key"],
    secret_key=config["secret_key"],
    secure=config["secure"]
)

objects = list(client.list_objects(config["bucket_name"], recursive=True))
print(f"{len(objects)}")
for obj in objects:
    print(f"{obj.object_name}|{obj.size}")
EOF
)

FILE_COUNT=$(echo "$MINIO_CHECK" | head -1)
if [ "$FILE_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓${NC} Found ${FILE_COUNT} file(s) in MinIO:"
    echo "$MINIO_CHECK" | tail -n +2 | while IFS='|' read -r name size; do
        echo "  - $name ($size bytes)"
    done
else
    echo "✗ No files found in MinIO"
    exit 1
fi

# Step 6: Fetch bundle via API
echo ""
echo -e "${BLUE}[6/7]${NC} Fetching bundle via API..."
FETCHED=$(curl -s "http://localhost:8000/api/v1/fhir/bundle/${BUNDLE_ID}")
if echo "$FETCHED" | grep -q "resourceType"; then
    echo -e "${GREEN}✓${NC} Bundle retrieved successfully"
    echo "Bundle preview:"
    echo "$FETCHED" | python3 -m json.tool | head -20
    echo "  ..."
else
    echo "✗ Failed to retrieve bundle"
    exit 1
fi

# Step 7: Check Redis events
echo ""
echo -e "${BLUE}[7/7]${NC} Checking Redis for published events..."
REDIS_CHECK=$(docker compose exec -T redis redis-cli << 'EOF'
PUBSUB CHANNELS surveillance:*
EOF
)

if echo "$REDIS_CHECK" | grep -q "surveillance:bundles"; then
    echo -e "${GREEN}✓${NC} Redis channel 'surveillance:bundles' is active"
else
    echo -e "${YELLOW}⚠${NC} Redis channel not subscribed (this is normal if no consumers are running)"
fi

# Summary
echo ""
echo "========================================"
echo -e "${GREEN}   Test Complete!${NC}"
echo "========================================"
echo ""
echo "Summary:"
echo "  Bundle ID: ${BUNDLE_ID}"
echo "  Files in MinIO: ${FILE_COUNT}"
echo "  API Status: Healthy"
echo ""
echo "Next steps:"
echo "  1. View MinIO Console: http://localhost:9001 (minioadmin/minioadmin123)"
echo "  2. View API Docs: http://localhost:8000/docs"
echo "  3. Check logs: docker compose logs -f fhir-api"
echo ""
echo "To test lab_dp workflow (requires setup):"
echo "  docker compose run --rm fhir-api python3 -m lab_dp.entrypoints.redis_eventconsumer"
echo ""
echo "To cleanup:"
echo "  docker compose down -v"
echo ""
