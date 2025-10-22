# Lab Data Product - Simple Makefile for testing

.DEFAULT_GOAL := test

# Start infrastructure services
up:
	docker compose up -d

# Run all tests
test:
	docker compose --profile test run --rm tests

# Run unit tests only (no dependencies needed)
unit-tests:
	docker compose run --rm --no-deps tests pytest tests/unit/ -v

# Run e2e tests only
e2e-tests:
	docker compose --profile test run --rm tests pytest tests/e2e/ -v

# Build image
build:
	docker compose build

# Stop services
down:
	docker compose down

# Clean up with volumes
clean:
	docker compose down -v

.PHONY: up test unit-tests e2e-tests build down clean