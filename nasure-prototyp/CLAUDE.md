# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development Setup
```bash
# Install package in development mode
cd src && pip install -e .

# Or install dependencies only
pip install -r requirements.txt

# Start infrastructure services
docker-compose up -d postgres redis minio

# Run database migrations
psql -h localhost -U lab_dp_user -d lab_dp_db -f migrations/001_initial_schema.sql

# Start FHIR Ingestion Microservice (local development)
cd src && uvicorn fhir_ingestion.entrypoints.fhir_api:app --reload --port 8000

# Start Lab Data Product Microservice (local development)
cd src && python -m lab_dp.entrypoints.event_processor
```

### Package Installation
```bash
# Install as editable package (development)
cd src && pip install -e .

# Install with test dependencies
cd src && pip install -e ".[test]"

# Install with development dependencies
cd src && pip install -e ".[dev]"

# Install production package
cd src && pip install .
```

### Docker Development
```bash
# Build and start all services
docker-compose up -d

# Start only infrastructure services
docker-compose up -d postgres redis minio

# Build specific service
docker-compose build fhir-ingestion
docker-compose build lab-dp-processor

# View logs for specific services
docker-compose logs -f fhir-ingestion
docker-compose logs -f lab-dp-processor

# Scale specific service
docker-compose up -d --scale fhir-ingestion=3
```

### Testing
```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_domain_model.py
pytest tests/test_api.py

# Run example ingestion script
python examples/test_minimal_model.py
```

## Architecture Overview

This is a domain-driven data product for laboratory surveillance, following microservice architecture patterns with event-driven communication.

### Microservices Structure

The codebase is organized as a monorepo with separate microservices:

#### **Shared Components** (`src/shared/`)
- **Domain Layer**: `src/shared/domain/` - Contains core business entities (LaboratoryReport, commands)
- **FHIR Processing**: `src/shared/fhir/` - FHIR transformation system for CH-eLM bundles
- **Service Layer**: `src/shared/service_layer/` - Unit of Work, message bus patterns
- **Adapters**: `src/shared/adapters/` - Repository patterns, Redis publisher
- **Services**: `src/shared/services/` - Shared utilities like pseudonymization

#### **FHIR Ingestion Microservice** (`src/fhir_ingestion/`)
- **API Endpoints**: `src/fhir_ingestion/entrypoints/` - FastAPI for FHIR bundle ingestion
- **Command Handlers**: `src/fhir_ingestion/service_layer/` - FHIR storage logic
- **Entry Point**: `src/fhir_ingestion/main.py` - Service startup

#### **Lab Data Product Microservice** (`src/lab_dp/`)
- **Event Processors**: `src/lab_dp/entrypoints/` - Redis event listeners
- **Command Handlers**: `src/lab_dp/service_layer/` - Data product generation logic
- **Storage**: `src/lab_dp/storage/` - PostgreSQL repositories
- **Entry Point**: `src/lab_dp/main.py` - Service startup

#### **Configuration** (`src/config.py`)
- Centralized environment-based configuration for all services

### FHIR Processing System with IG Automation

The system processes FHIR bundles using machine-readable Implementation Guide components:

- **IG-Based Transformation**: Automatically extracts mappings from FHIR IG ValueSets and CodeSystems
- **Supported Versions**: CH-eLM v1.0.0 - 1.11.0 (FHIR R4)
- **Dynamic Mappings**: LOINC→pathogen and SNOMED→result mappings auto-extracted from IG
- **Automated Config Generation**: Disease configurations generated from IG StructureDefinitions
- **Entry Points**:
  - `MinimalFHIRTransformer` in `src/lab_dp/fhir/minimal_transformer.py`
  - FHIR transformation logic in `src/lab_dp/fhir/`
  - Configuration-based pathogen mapping

### Configuration-Driven Disease Support

Pathogen-specific behavior is configured via mapping dictionaries:

- **CH_ELM_PATHOGEN_MAPPINGS**: LOINC code to pathogen mappings
- **SNOMED_RESULT_MAPPINGS**: SNOMED code to result interpretation mappings
- **Configuration**: Located in `src/lab_dp/domain/minimal_model.py`

### Dual API Structure

1. **FHIR API** (`entrypoints/fhir_api.py`): CH-eLM FHIR bundle processing API
2. **Additional APIs**: Can be added for specific surveillance use cases

### Event-Driven Architecture

- **Redis Pub/Sub**: Real-time event publishing for surveillance alerts
- **Domain Events**: Event-driven processing for surveillance alerts
- **Event Processor**: Background service for event handling

### Infrastructure Dependencies

- **PostgreSQL**: Primary data storage with health checks
- **Redis**: Event publishing and caching
- **MinIO**: S3-compatible storage for raw FHIR bundles
- **Grafana**: Monitoring dashboard (optional)

### Key Environment Variables

```bash
DATABASE_URL=postgresql://lab_dp_user:lab_dp_pass@postgres:5432/lab_dp_db
REDIS_URL=redis://redis:6379
PATIENT_IDENTITY_SERVICE_URL=http://patient-identity:8001
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
MINIO_BUCKET=lab-raw-data
```

### Privacy and Security

- **Patient Tokenization**: Privacy-preserving patient identification via `PatientTokenService`
- **De-identification**: Patient data is tokenized before storage
- **Jurisdictional Reporting**: Configurable privacy settings per disease category

## Adding New Features

### Adding New Pathogens (IG-Based)
1. **Automatic Discovery**: New pathogens in IG ValueSets are automatically detected
2. **Auto-Generated Config**: Run `generate_ig_based_configs()` to create YAML configurations
3. **Custom Overrides**: Add pathogen-specific quality rules in generated config files
4. **Database Schema**: Update surveillance alerts if needed for new pathogen types

### Adding New FHIR Versions (IG-Based)
1. **Update IG Package**: Change package version in `IGBasedTransformer` configuration
2. **Refresh Mappings**: Call `transformer.refresh_ig_mappings()` to update from new IG
3. **Regenerate Configs**: Run `generate_ig_based_configs()` for updated disease configurations
4. **Version Detection**: Update `FHIRVersionDetector` if IG introduces new detection patterns

### Refreshing IG-Based Configurations
```python
# Refresh mappings from updated IG
transformer = IGBasedTransformer("ch.fhir.ig.ch-elm", "1.12.0")
transformer.refresh_ig_mappings()

# Regenerate all disease configurations
configs = generate_ig_based_configs("ch.fhir.ig.ch-elm", output_dir="./configs")
```

### Adding New Disease Categories
1. Update `DiseaseCategory` enum in `generic_api.py`
2. Create base configuration file following `base_sti.yml` pattern
3. Implement disease-specific surveillance logic in `GenericSurveillanceService`
4. Add API endpoints for the new category

## Quality Metrics and SLA Targets

- **Data Freshness**: < 24 hours for routine surveillance
- **Completeness**: > 90% for reportable conditions
- **Availability**: 99.5% uptime target
- **Quality Score Alerts**: < 0.8 triggers medium severity alert