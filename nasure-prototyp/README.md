# Nasure Prototyp

**Current Status**: ✅ Event-driven processing with MinIO-first storage

## 🏗️ Event-Driven Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    API LAYER (FastAPI)                         │
├─────────────────────────────────────────────────────────────────┤
│  POST /api/v1/fhir/ingest                                      │
│  ├─ Receives CH-eLM FHIR Bundle                               │
│  ├─ Publishes FHIRBundleReceived event                        │
│  └─ Returns bundle_id for status tracking                      │
│                                                                 │
│  GET /api/v1/status/{bundle_id}                                │
│  GET /api/v1/reports                                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              EVENT-DRIVEN PROCESSING FLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ 1. FHIRBundleReceived Event ────────────────────────────┐  │
│  │   └─ Store raw FHIR bundle in MinIO FIRST (priority)    │  │
│  │       └─ Publishes FHIRBundleStored event               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                │                               │
│                                ▼                               │
│  ┌─ 2. FHIRBundleStored Event ──────────────────────────────┐  │
│  │   └─ Triggers data product generation                    │  │
│  │       └─ Publishes DataProductRequested event           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                │                               │
│                                ▼                               │
│  ┌─ 3. DataProductRequested Event ──────────────────────────┐  │
│  │   ├─ Reads FHIR bundle from MinIO                        │  │
│  │   ├─ Calls Patient Mapping Service                       │  │
│  │   ├─ Calls Organization Mapping Service                  │  │
│  │   ├─ Transforms to surveillance data product             │  │
│  │   └─ Stores in PostgreSQL                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐│
│  │ MinIO           │  │ PostgreSQL       │  │ External APIs   ││
│  │ (Raw FHIR)      │  │ (Data Product)   │  │ (Mapping)       ││
│  │                 │  │                  │  │                 ││
│  │ • YYYY/MM/DD/   │  │ • LaboratoryReport│  │ • Patient       ││
│  │   structure     │  │   table          │  │   Mapping API   ││
│  │ • Immutable     │  │ • Surveillance   │  │ • Organization  ││
│  │   storage       │  │   optimized      │  │   Mapping API   ││
│  │ • Audit trail   │  │ • Indexing       │  │ • (Returns      ││
│  │                 │  │                  │  │   random IDs)   ││
│  └─────────────────┘  └──────────────────┘  └─────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MAPPING SERVICES                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────┐│
│  │ Patient Mapping │  │ Organization     │  │ FHIR            ││
│  │ Service         │  │ Mapping Service  │  │ Transformer     ││
│  │                 │  │                  │  │                 ││
│  │ AHV Number →    │  │ GLN → Anonymous  │  │ LOINC → pathogen ││
│  │ Anonymous ID    │  │ Organization ID  │  │ 697-3 → NG      ││
│  │                 │  │                  │  │                 ││
│  │ • Deterministic │  │ • Deterministic  │  │ • CH-eLM v1.10  ││
│  │   UUID from     │  │   UUID from GLN  │  │   Mappings      ││
│  │   AHV SHA256    │  │   SHA256         │  │ • SNOMED →      ││
│  │ • (Ready for    │  │ • (Ready for     │  │   Result Type   ││
│  │   external API) │  │   external API)  │  │                 ││
│  └─────────────────┘  └──────────────────┘  └─────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DATA PRODUCT INTERFACE                        │
├─────────────────────────────────────────────────────────────────┤
│  LaboratoryReport (Minimal Essential Data)                     │
│  ├─ patient_id: "c4ca4238-a0b9..."        # Anonymous ID     │
│  ├─ pathogen: "neisseria_gonorrhoeae"     # Primary pathogen │
│  ├─ performing_lab_id: "a9b8c7d6..."      # Anonymous lab ID │
│  ├─ ordering_facility_id: "e5f4g3h2..."   # Anonymous fac ID │
│  ├─ bundle_id: "1Doc-NeisseriaGonorrhoeae"                   │
│  ├─ fhir_identifier: "urn:uuid:1901332d..."                  │
│  ├─ report_timestamp: "2023-07-14T16:00:00+02:00"           │
│  └─ observations: [test results with LOINC→pathogen mapping] │
└─────────────────────────────────────────────────────────────────┘
```

### Process Flow

```
1. FHIR Bundle Received → MinIO Storage (PRIORITY 1)
   ├─ Immediate raw data persistence
   ├─ Immutable audit trail
   └─ Processing can continue from stored state

2. MinIO Storage Complete → Data Product Generation
   ├─ Asynchronous processing
   ├─ No data loss if processing fails
   └─ Can replay from stored FHIR

3. Individual Service Calls → Anonymous Mappings
   ├─ Patient AHV → Anonymous UUID
   ├─ Organization GLN → Anonymous UUID
   └─ Ready for external API integration

```

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- curl (for manual testing)

### Quick Start with Automated Tests

```bash
# Run all tests (starts infrastructure automatically)
make test

# Run only unit tests (no infrastructure needed)
make unit-tests

# Run only E2E tests
make e2e-tests
```

### Manual Testing - Complete Workflow

This guide walks you through manually testing the complete data flow from FHIR ingestion to data product storage.

#### Step 1: Start Infrastructure

```bash
# Start all services (PostgreSQL, Redis, MinIO, FHIR API)
docker compose up -d

# Check all services are running
docker compose ps
```

Expected output:
```
NAME                STATUS              PORTS
fhir-api           running             0.0.0.0:8000->8000/tcp
minio              running             0.0.0.0:9000-9001->9000-9001/tcp
postgres           running             0.0.0.0:5432->5432/tcp
redis              running             0.0.0.0:6379->6379/tcp
```

#### Step 2: Send Test FHIR Bundle

```bash
# Send a sample CH-eLM FHIR bundle
curl -X POST "http://localhost:8000/api/v1/fhir/ingest" \
     -H "Content-Type: application/json" \
     -d @tests/examples/fhir_bundles/sample_ch_elm_bundle.json

# Expected response:
# {
#   "status": "accepted",
#   "bundle_id": "a7c8f2e4-...",
#   "message": "FHIR bundle processing started",
#   "received_at": "2025-01-15T10:30:00.123456"
# }
```

**Save the bundle_id** from the response - you'll need it for the next steps!

#### Step 3: Verify Bundle in MinIO

```bash
# Set your bundle_id from Step 2
BUNDLE_ID="a7c8f2e4-..."  # Replace with your actual bundle_id

# Option 1: Use MinIO Console (Web UI)
# Open http://localhost:9001 in browser
# Login: minioadmin / minioadmin123
# Navigate to: lab-raw-data bucket
# Look for: fhir_bundles/YYYY/MM/DD/*.json

# Option 2: Use mc (MinIO CLI) - requires installation
mc alias set local http://localhost:9000 minioadmin minioadmin123
mc ls local/lab-raw-data/fhir_bundles/ --recursive

# Option 3: Use Python to check MinIO
docker compose exec fhir-api python3 << EOF
from minio import Minio
from config import get_minio_config

config = get_minio_config()
client = Minio(
    endpoint=config["endpoint"],
    access_key=config["access_key"],
    secret_key=config["secret_key"],
    secure=config["secure"]
)

# List all objects in bucket
print("\n=== Files in MinIO ===")
for obj in client.list_objects(config["bucket_name"], recursive=True):
    print(f"✓ {obj.object_name} ({obj.size} bytes)")
EOF
```

#### Step 4: Check Redis for Published Events

```bash
# Connect to Redis and check for published events
docker compose exec redis redis-cli

# Inside Redis CLI:
# Subscribe to surveillance channel (this will wait for new events)
SUBSCRIBE surveillance:bundles

# Or check recent messages (in a new terminal):
docker compose exec redis redis-cli MONITOR

# Exit Redis CLI with Ctrl+C
```

#### Step 5: Verify Data in PostgreSQL (fhir_ingestion)

```bash
# Check if bundle metadata exists in PostgreSQL
docker compose exec postgres psql -U lab_dp_user -d lab_dp_db << EOF
-- Show all tables
\dt

-- If fhir_ingestion has tables, query them
-- (Currently fhir_ingestion uses MinIO only, so this may be empty)
SELECT COUNT(*) as total_bundles FROM bundles;
EOF
```

#### Step 6: Test Complete lab_dp Workflow

The lab_dp consumer runs automatically when you start services with `docker compose up -d`.
It listens to Redis events and automatically processes bundles.

```bash
# Check lab_dp consumer logs
docker compose logs -f lab-dp-consumer

# You should see:
# lab-dp-consumer  | Lab DP Redis pubsub consumer starting
# lab-dp-consumer  | ✓ Database tables created and ORM mappers initialized
# lab-dp-consumer  | Subscribed to 'surveillance:bundles' channel, waiting for messages...

# After sending a bundle (Step 2), you'll see:
# lab-dp-consumer  | Received message: ...
# lab-dp-consumer  | Processing BundleStored event for bundle abc123...
# lab-dp-consumer  | Successfully processed bundle abc123

# Check lab_dp database
docker compose exec postgres psql -U lab_dp_user -d lab_dp_db << 'EOF'
-- Show all tables
\dt

-- Show lab data products
SELECT
    product_id,
    bundle_id,
    patient_id,
    pathogen_code,
    pathogen_description,
    interpretation,
    timestamp
FROM products
ORDER BY timestamp DESC
LIMIT 10;
EOF
```

#### Step 7: Fetch Bundle via API

```bash
# Retrieve the stored bundle by ID
BUNDLE_ID="a7c8f2e4-..."  # Use your bundle_id from Step 2

curl -X GET "http://localhost:8000/api/v1/fhir/bundle/${BUNDLE_ID}"

# Expected: Full FHIR bundle JSON
```

#### Step 8: Health Checks

```bash
# Check FHIR API health
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "lab-dp-fhir-api",
#   "timestamp": "2025-01-15T10:30:00.123456Z"
# }
```

#### Step 9: View Logs

```bash
# View all service logs
docker compose logs -f

# View specific service logs
docker compose logs -f fhir-api
docker compose logs -f redis
docker compose logs -f postgres
docker compose logs -f minio
```

#### Step 10: Cleanup

```bash
# Stop all services
docker compose down

# Remove all data (including volumes)
docker compose down -v
```

### Quick Verification Script

Here's a complete script to test the workflow:

```bash
#!/bin/bash
set -e

echo "=== Testing FHIR Ingestion Workflow ==="

# 1. Start services
echo "1. Starting services..."
docker compose up -d
sleep 5

# 2. Send bundle
echo "2. Sending FHIR bundle..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/fhir/ingest" \
     -H "Content-Type: application/json" \
     -d @tests/examples/fhir_bundles/sample_ch_elm_bundle.json)

echo "$RESPONSE"
BUNDLE_ID=$(echo "$RESPONSE" | grep -o '"bundle_id":"[^"]*' | cut -d'"' -f4)
echo "Bundle ID: $BUNDLE_ID"

# 3. Wait for processing
echo "3. Waiting for processing..."
sleep 3

# 4. Check MinIO
echo "4. Checking MinIO..."
docker compose exec fhir-api python3 -c "
from minio import Minio
from config import get_minio_config
config = get_minio_config()
client = Minio(config['endpoint'], config['access_key'], config['secret_key'], config['secure'])
count = len(list(client.list_objects(config['bucket_name'], recursive=True)))
print(f'✓ Found {count} files in MinIO')
"

# 5. Fetch bundle
echo "5. Fetching bundle via API..."
curl -s "http://localhost:8000/api/v1/fhir/bundle/${BUNDLE_ID}" | head -c 200
echo "..."

echo ""
echo "=== Test Complete ==="
echo "To cleanup: docker compose down -v"
```

### Quick Testing Scripts

We provide two scripts for easy manual testing:

#### 1. Complete Workflow Test

```bash
# Run complete end-to-end test
./scripts/test_workflow.sh
```

This script:
- ✓ Starts all services
- ✓ Checks API health
- ✓ Sends a test FHIR bundle
- ✓ Verifies storage in MinIO
- ✓ Fetches bundle via API
- ✓ Checks Redis events
- ✓ Provides summary and next steps

#### 2. Storage Verification

```bash
# Check current state of MinIO and PostgreSQL
./scripts/check_storage.sh
```

This script shows:
- All files in MinIO bucket
- PostgreSQL tables and data (if any)
- Recent Redis activity

### Access Services

- **FHIR API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **MinIO Console**: http://localhost:9001 (minioadmin / minioadmin123)
- **PostgreSQL**: localhost:5432 (lab_dp_user / lab_dp_pass)
- **Redis**: localhost:6379

### Common Commands

```bash
# Start services
make up

# Stop services
make down

# Clean everything (including volumes)
make clean

# Build containers
make build

# Run tests
make test

# Quick manual test
./scripts/test_workflow.sh

# Check storage status
./scripts/check_storage.sh
```
