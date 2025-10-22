FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install Python dependencies from requirements
COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-test.txt

# Copy source code, tests, and scripts
COPY src/ ./src/
COPY tests/ ./tests/
COPY scripts/ ./scripts/

# Install as editable package
WORKDIR /app/src
RUN pip install -e .

# Set Python path
ENV PYTHONPATH=/app/src:/app

# Go back to app directory
WORKDIR /app

# Expose port
EXPOSE 8000

# Default command - run API (can be overridden)
CMD ["uvicorn", "fhir_ingestion.entrypoints.fhir_api:app", "--host", "0.0.0.0", "--port", "8000"]