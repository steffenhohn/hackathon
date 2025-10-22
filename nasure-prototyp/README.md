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

**Start Infrastructure:**

```bash
make up
```

**Run tests**

```bash
make test
```

**Manual API calls**

```bash
# Send FHIR bundle via API
curl -X POST "http://localhost:8000/api/v1/fhir/ingest" \
     -H "Content-Type: application/json" \
     -d @examples/ch_elm_bundles/anthrax_1.json

# Check processing status
curl "http://localhost:8000/api/v1/status/{bundle_id}"



5. **Access Services:**
- **API**: http://localhost:8000 (FastAPI)
- **MinIO Console**: http://localhost:9001 (Raw FHIR storage)


```
