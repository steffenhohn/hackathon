# Lab Data Product - Simple Makefile for testing

.DEFAULT_GOAL := test

# Start infrastructure services
up:
	docker compose up -d

# Run all tests
test: up
	docker compose run --rm --no-deps --entrypoint=pytest fhir-api /app/tests/unit /app/tests/integration /app/tests/e2e -v

# Run unit tests only (no dependencies needed)
unit-tests:
	docker compose run --rm --no-deps --entrypoint=pytest fhir-api /app/tests/unit -v

# Run integration tests
integration-tests: up
	docker compose run --rm --no-deps --entrypoint=pytest fhir-api /app/tests/integration -v

# Run e2e tests
e2e-tests: up
	docker compose run --rm --no-deps --entrypoint=pytest fhir-api /app/tests/e2e -v

# Build image
build:
	docker compose build

# Stop services
down:
	docker compose down

# Clean up with volumes
clean:
	docker compose down -v

.PHONY: up test unit-tests integration-tests e2e-tests build down clean