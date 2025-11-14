# NASURE Prototyp

**Current Status of Functionality**: 
✅ Ingestion of CH-ELM FHIR Bundles (via API or through web form)
✅ Processing of lab reports and creation of lab data product
✅ Pseudonoymisation of patient data
✅ Correlation of lab reports into cases
✅ Display of active cases in KAD Web Dashboard
✅ Basic dashboard with lab report quality metrics


## 🏗️ System Architecture Overview

The NASURE system implements a complete surveillance data processing pipeline with 5 microservices. The following technical concepts have been adopted in this prototype:

✅ Decoupled services based on domains
✅ Event-based architecture (with room for improvement)
✅ Provision of data products for external consumption
✅ Integration of patient service for pseudonoymisation
✅ CQRS - Command / Query Responsibility Segregation


```
┌─────────────────────────────────────────┐
│            FHIR INGESTION               │
│  📥 Receive & Store Raw FHIR Data      │
├─────────────────────────────────────────┤
│ POST /api/v1/fhir/ingest               │
│ ├─ Validate FHIR Bundle                │
│ ├─ Generate bundle_id (UUID)           │
│ ├─ Store in MinIO (PRIORITY #1)        │
│ │  Path: fhir_bundles/YYYY/MM/DD/      │
│ │        bundle-{id}.json              │
│ └─ Return bundle_id immediately        │
└─────────────────────────────────────────┘
                    │
                    ▼
          ✨ PUBLISHES EVENT ✨
    📢 "surveillance:bundles" channel
    Event: BundleStored

┌─────────────────────────────────────────┐
│        LAB DATA PRODUCT SERVICE         │
│  🔬 Transform FHIR → Surveillance Data  │
├─────────────────────────────────────────┤
│ 📡 LISTENS TO: "surveillance:bundles"   │
│                                         │
│ WHEN: BundleStored event received       │
│ PROCESS:                                │
│ 1️⃣ Fetch FHIR bundle from MinIO        │
│ 2️⃣ Extract Patient → Call Patient API   │
│ 3️⃣ Extract DiagnosticReport            │
│ 4️⃣ Map LOINC codes → Pathogen names     │
│ 5️⃣ Store in PostgreSQL (lab_dp_db)     │
│ 6️⃣ Update metrics (CQRS read model)     │
└─────────────────────────────────────────┘

                    │
                    ▼
         🔄 CALLS PATIENT SERVICE
    POST /api/v1/patient/pseudonymize
    
                    │
                    ▼
      💾 STORES IN POSTGRESQL
    Table: products
    Table: metrics (CQRS Read Model)
                    │
                    ▼
          ✨ PUBLISHES EVENT ✨
    📢 "surveillance:products" channel
    
    Event: DataProductCreated

┌─────────────────────────────────────────┐
│        CASE MANAGEMENT SERVICE          │
│  🏥 Correlate Reports → Create Cases    │
├─────────────────────────────────────────┤
│ 📡 LISTENS TO: "surveillance:products"  │
│                                         │
│ WHEN: DataProductCreated event received │
│ PROCESS:                                │
│ 1️⃣ Check existing cases for patient     │
│    (same patient + pathogen + 28 days)  │
│ 2️⃣ IF MATCH → Link to existing case     │
│ 3️⃣ IF NO MATCH → Create new case        │
│ 4️⃣ Link data product to case            │
│ 5️⃣ Classify case (sicherer Fall, etc.)  │
│ 6️⃣ Store in case_db                     │
└─────────────────────────────────────────┘
                    │
                    ▼
      💾 STORES IN POSTGRESQL (case_db)
    
    Table: cases   
    Table: case_to_product (Relationships)
                    │
                    ▼
          ✨ PUBLISHES EVENT ✨
    📢 "surveillance:cases" channel
    Event: CaseCreated (only for new cases)

┌─────────────────────────────────────────┐
│            KAD DASHBOARD                │
│  🖥️ Case Management Interface          │
├─────────────────────────────────────────┤
│ AUTHENTICATION:                         │
│ Username: admin / Password: admin       │
│                                         │
│ PUBLIC FEATURES:                        │
│ 📊 Case Statistics & Metrics            │
│ 🔍 Case Search & Filtering              │
│ 📈 Real-time Updates (auto-refresh)     │
│ 📄 Linked Lab Reports                   │
│ 💾 Data Export (CSV/JSON)               │
│                                         │
│ AUTHENTICATED FEATURES:                 │
│ 👤 Patient Data (de-anonymized)         │
│   ├─ Real names (encrypted lookup)      │
│   ├─ AHV numbers                        │
│   └─ Full patient details               │
│ ⚡ Case Status Management                │
│ 🔗 Product Linking                      │
└─────────────────────────────────────────┘
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

### Events

```bash
# fhir_ingestion/domain/events
Event: BundleStored
    ├─ bundle_id: "abc-123-def"
    ├─ object_key: "fhir_bundles/2024/01/15/bundle-abc.json"
    ├─ bundle_type: "CH-eLM"
    ├─ source_system: "lab_system_x"
    ├─ stored_at: "2024-01-15T10:30:00Z"
    └─ bundle_size: 2048

# lab_dp/domain/events
Event: DataProductCreated
    ├─ product_id: "def-456-ghi"
    ├─ patient_id: "c4ca4238..." (pseudonymized)
    ├─ pathogen_code: "697-3"
    ├─ pathogen_description: "Neisseria gonorrhoeae"
    ├─ timestamp: "2024-01-15T08:45:00Z" (lab timestamp)
    ├─ stored_at: "2024-01-15T10:30:00Z" (MinIO storage)
    └─ created_at: "2024-01-15T10:30:05Z" (processing time)

# case/domain/events
Event: CaseCreated (only for new cases)
    ├─ case_id: "ghi-789-jkl"
    └─ created_at: "2024-01-15T10:30:10Z"

# patient service: no events published, because it operates synchronously
```

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- curl (for manual testing)

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- curl (for testing)

### Quick Start with Automated Tests

⚠️ Note: this is not implement for all services!

```bash
# Run all tests (starts infrastructure automatically)
make test

# Run only unit tests (no infrastructure needed)
make unit-tests

# Run only E2E tests
make e2e-tests
```

### 1. Start All Services

```bash
# Clone the repository
git clone <repository-url>
cd nasure-prototyp

# Start all infrastructure and services
docker compose up -d

# Check all services are running
docker compose ps

# Check individual logs
docker compose logs -f
or
docker compose logs -f <name-of-service>
```

Expected services:
- **Bundle Generator**: Port 8010
- **Case Dashboard**: Port 8501
- **FHIR API**: Port 8000
- **Patient Service**: Port 8002  
- **Case Management API**: Port 8003
- **Lab Data Product API**: Port 8001
- **PostgreSQL**: Port 5432
- **Redis**: Port 6379
- **MinIO**: Port 9000/9001
- **pgAdmin**: Port 5050
- **RedisInsight**: Port 8011

### 2. Access the Dashboard

Open your browser and navigate to:
- **Main Dashboard**: http://localhost:8501
- **FHIR Bundle Creator**: http://localhost:8010
- **FHIR Ingestion Documentation**: http://localhost:8000/docs

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

#### (Optional) Step 3: Verify Bundle in MinIO

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

#### Step 4: (Optional) Check Redis for Published Events

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

OR

Use redisinsight which was also installed with docker compose.

Just open http://localhost:8011/
and you will immidiatly see the database "redis:6379".

Now you may switch to Pub/Sub and register for the channels, e.g. "surveillance:bundles".

#### Step 5: (Optional) Verify Data in PostgreSQL (fhir_ingestion)

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

OR

Use pgadmin which was also installed with docker compose.

Just open http://localhost:5050/
and use admin@example.com/admin for login.

The Postgres DB lab_dp_db is already pre-configured.

Just choose Servers/Nasure Postgres/Databases/lab_dp_db from the left menu.

Attention:

Because of an unsolved error in the setup, you have to enter the password "lab_dp_pass" and
click "Save Password" once.

#### Step 6: (Optional) Test Complete lab_dp Workflow

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

### Manual Tests

#### Send FHIR Bundle

```bash
# Send a test FHIR bundle through the complete pipeline
curl -X POST "http://localhost:8000/api/v1/fhir/ingest" \
     -H "Content-Type: application/json" \
     -d @tests/examples/fhir_bundles/sample_ch_elm_bundle.json

# Expected response with bundle_id
# Watch the dashboard for new cases appearing
```
#### Pseudonymize Patient

```bash
# Pseudonymize Patient
curl -X POST "http://localhost:8001/api/v1/patient/pseudonymize" \
  -H "Content-Type: application/json" \
  -d '{
    "resourceType": "Patient",
    "identifier": [{"value": "7561234567890"}],
    "name": [{"family": "Doe", "given": ["John"]}],
    "gender": "male",
    "birthDate": "1990-01-01",
    "address": [{"state": "ZH"}]
  }'```
# Response:
{
  "patient_id": "c4ca4238-a0b9-1de6-9412-56a6b84e5a9b"
}

# Get Patient Details
curl "http://localhost:8002/api/v1/patient/c4ca4238-a0b9-1de6-9412-56a6b84e5a9b"

# Response:
{
  "ahv_number": "7561234567890",
  "family_name": "Doe",
  "given_name": "John",
  "gender": "male",
  "birthdate": "1990-01-01",
  "canton": "ZH"
}
```

#### Lab Data Product

```bash
# Get all data products
GET /api/v1/data-products?limit=100&offset=0

# Get specific data product
GET /api/v1/data-product/{product_id}

# Get products by pathogen
GET /api/v1/data-products/pathogen/{pathogen_code}

# Get products by patient and pathogen
GET /api/v1/data-products/patient/{patient_id}/pathogen/{pathogen_code}

# Quality metrics
GET /api/v1/metrics/quality

# Pathogen count (last 24h)
GET /api/v1/metrics/pathogen/{pathogen_code}
```

#### Case Management

```bash
# Get all cases (paginated with filters)
GET /api/v1/cases?page=1&page_size=20&status=neu&canton=BE

# Get specific case
GET /api/v1/cases/{case_id}

# Create Case
curl -X POST "http://localhost:8003/api/v1/cases" \
     -H "Content-Type: application/json" \
     -d '{
       "product_id": "0760c467-25b9-42d3-87b1-5658c02e5a9b",
       "patient_id": "c4ca4238-a0b9-1de6-9412-56a6b84e5a9b",
       "pathogen_code": "32781-7",
       "pathogen_description": "Legionella pneumophila",
       "lab_timestamp": "2024-10-24T10:30:00Z",
       "canton": "BE"
     }'

# Get products linked to case
GET /api/v1/cases/{case_id}/products


**🏥 Built with ❤️ by the NASURE team 2025**
