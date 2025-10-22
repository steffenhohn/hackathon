"""Configuration settings for lab data product."""

import os


def get_postgres_uri():
    """Get PostgreSQL connection URI from environment variables."""
    host = os.environ.get("DB_HOST", "localhost")
    port = 5433 if host == "localhost" else 5432
    password = os.environ.get("DB_PASSWORD", "lab_dp_pass")
    user = os.environ.get("DB_USER", "lab_dp_user")
    db_name = os.environ.get("DB_NAME", "lab_dp_db")
    return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"


def get_redis_host_and_port():
    """Get Redis connection details from environment variables."""
    host = os.environ.get("REDIS_HOST", "localhost")
    port = 6379 if host == "localhost" else 6379
    return dict(host=host, port=port)


def get_redis_url():
    """Get Redis URL from environment variables."""
    redis_config = get_redis_host_and_port()
    return f"redis://{redis_config['host']}:{redis_config['port']}"


def get_minio_config():
    """Get MinIO connection configuration from environment variables."""
    host = os.environ.get("MINIO_HOST", "localhost")
    endpoint = f"{host}:9000" if host == "localhost" else f"{host}:9000"
    access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin123")
    bucket_name = os.environ.get("MINIO_BUCKET", "lab-raw-data")
    secure = os.environ.get("MINIO_SECURE", "false").lower() == "true"

    return dict(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        bucket_name=bucket_name,
        secure=secure
    )


def get_api_url():
    """Get API URL from environment variables."""
    host = os.environ.get("API_HOST", "localhost")
    port = 8000 if host == "localhost" else 8000
    return f"http://{host}:{port}"