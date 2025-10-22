#!/usr/bin/env python3
"""
Clean MinIO test bucket.

Usage:
    python scripts/dev_cleanup.py
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

try:
    from minio import Minio
    from minio.error import S3Error
    from config import get_minio_config
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Make sure you have installed the requirements:")
    print("pip install -r requirements.txt")
    sys.exit(1)


def clean_minio_bucket() -> bool:
    """Clean MinIO test bucket."""
    try:
        minio_config = get_minio_config()
        bucket_name = minio_config["bucket_name"]

        minio_client = Minio(
            endpoint=minio_config["endpoint"],
            access_key=minio_config["access_key"],
            secret_key=minio_config["secret_key"],
            secure=minio_config["secure"]
        )

        print(f"Cleaning MinIO bucket '{bucket_name}'...")

        if not minio_client.bucket_exists(bucket_name):
            print(f"Bucket '{bucket_name}' doesn't exist - nothing to clean")
            return True

        objects = list(minio_client.list_objects(bucket_name, recursive=True))

        if not objects:
            print("Bucket is already empty")
            return True

        print(f"Deleting {len(objects)} objects...")

        for obj in objects:
            try:
                minio_client.remove_object(bucket_name, obj.object_name)
            except S3Error as e:
                print(f"Failed to delete {obj.object_name}: {e}")

        print(f"Deleted {len(objects)} objects from MinIO bucket")
        return True

    except Exception as e:
        print(f"MinIO cleanup failed: {e}")
        return False


def main():
    if clean_minio_bucket():
        print("Cleanup completed successfully")
    else:
        print("Cleanup completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()