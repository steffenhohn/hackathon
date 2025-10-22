# pylint: disable=redefined-outer-name
import time
from pathlib import Path

import pytest
import redis
import requests
from minio import Minio
from tenacity import retry, stop_after_delay

from config import get_api_url, get_redis_host_and_port, get_minio_config

pytest.register_assert_rewrite("tests.e2e.api_client")


@retry(stop=stop_after_delay(60))
def wait_for_webapp_to_come_up():
    return requests.get(f"{get_api_url()}/health", timeout=1)


@retry(stop=stop_after_delay(30))
def wait_for_redis_to_come_up():
    r = redis.Redis(**get_redis_host_and_port())
    return r.ping()


@retry(stop=stop_after_delay(30))
def wait_for_minio_to_come_up():
    minio_config = get_minio_config()
    client = Minio(
        endpoint=minio_config["endpoint"],
        access_key=minio_config["access_key"],
        secret_key=minio_config["secret_key"],
        secure=minio_config["secure"]
    )
    return client.list_buckets()


@pytest.fixture
def restart_api():
    (Path(__file__).parent / "../../src/fhir_ingestion/entrypoints/fhir_api.py").touch()
    time.sleep(0.5)
    wait_for_webapp_to_come_up()


@pytest.fixture
def restart_redis():
    wait_for_redis_to_come_up()


@pytest.fixture
def minio_client():
    wait_for_minio_to_come_up()
    minio_config = get_minio_config()
    return Minio(
        endpoint=minio_config["endpoint"],
        access_key=minio_config["access_key"],
        secret_key=minio_config["secret_key"],
        secure=minio_config["secure"]
    )


@pytest.fixture
def redis_client():
    wait_for_redis_to_come_up()
    return redis.Redis(**get_redis_host_and_port())


@pytest.fixture
def clean_minio():
    """Clean MinIO bucket before tests"""
    minio_config = get_minio_config()
    client = Minio(
        endpoint=minio_config["endpoint"],
        access_key=minio_config["access_key"],
        secret_key=minio_config["secret_key"],
        secure=minio_config["secure"]
    )

    bucket_name = minio_config["bucket_name"]

    # Create bucket if it doesn't exist
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    # Clean existing objects
    objects = client.list_objects(bucket_name, recursive=True)
    for obj in objects:
        client.remove_object(bucket_name, obj.object_name)

    yield client

    # Cleanup after tests
    objects = client.list_objects(bucket_name, recursive=True)
    for obj in objects:
        client.remove_object(bucket_name, obj.object_name)