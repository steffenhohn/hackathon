#!/bin/bash
# Quick script to check data in MinIO and PostgreSQL

echo "========================================"
echo "   Storage Verification"
echo "========================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check MinIO
echo -e "${BLUE}MinIO Storage:${NC}"
echo "----------------------------------------"
docker compose exec -T fhir-api python3 << 'EOF'
from minio import Minio
from config import get_minio_config

config = get_minio_config()
client = Minio(
    endpoint=config["endpoint"],
    access_key=config["access_key"],
    secret_key=config["secret_key"],
    secure=config["secure"]
)

print(f"Bucket: {config['bucket_name']}\n")

objects = list(client.list_objects(config["bucket_name"], recursive=True))
if objects:
    print(f"Found {len(objects)} file(s):\n")
    for obj in objects:
        print(f"  ✓ {obj.object_name}")
        print(f"    Size: {obj.size} bytes")
        print(f"    Last Modified: {obj.last_modified}")
        print()
else:
    print("  No files found in MinIO")
EOF

echo ""
echo -e "${BLUE}PostgreSQL Database:${NC}"
echo "----------------------------------------"

# Check if lab_dp tables exist
docker compose exec -T postgres psql -U lab_dp_user -d lab_dp_db << 'EOF'
-- List all tables
\dt

-- Try to query lab_dp products table
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'products') THEN
        RAISE NOTICE 'Products table exists. Querying...';
    ELSE
        RAISE NOTICE 'Products table does not exist yet (normal if lab_dp not initialized)';
    END IF;
END
$$;

-- Show products if table exists
SELECT
    CASE
        WHEN EXISTS (SELECT FROM pg_tables WHERE tablename = 'products')
        THEN (SELECT COUNT(*)::text FROM products)
        ELSE 'N/A'
    END as product_count;

-- If products exist, show them
DO $$
BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE tablename = 'products') THEN
        PERFORM * FROM products;
        IF FOUND THEN
            RAISE NOTICE 'Showing recent products:';
        END IF;
    END IF;
END
$$;

-- Try to show recent products if they exist
SELECT
    product_id,
    bundle_id,
    patient_id,
    pathogen_code,
    interpretation,
    timestamp
FROM products
ORDER BY timestamp DESC
LIMIT 5;

EOF

echo ""
echo -e "${BLUE}Redis Activity:${NC}"
echo "----------------------------------------"
echo "Recent Redis activity (last 10 seconds):"
timeout 3 docker compose exec -T redis redis-cli MONITOR 2>/dev/null || echo "  (No recent activity)"

echo ""
echo "========================================"
echo "To view in web interfaces:"
echo "  MinIO Console: http://localhost:9001"
echo "    Login: minioadmin / minioadmin123"
echo "  API Docs: http://localhost:8000/docs"
echo "========================================"
