"""Setup script for lab-data-dp package following Cosmic Python pattern."""

from setuptools import setup, find_packages

setup(
    name="lab-data-dp",
    version="1.0.0",
    description="Laboratory Data Product - Event-driven FHIR surveillance system",
    author="Lab Data Product Team",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi",
        "uvicorn[standard]",
        "pydantic",
        "sqlalchemy",
        "psycopg2-binary",
        "alembic",
        "redis",
        "minio",
        "requests",
        "python-multipart",
        "python-jose[cryptography]",
        "passlib[bcrypt]",
        "email-validator",
    ],
    extras_require={
        "test": [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
            "httpx",
            "fakeredis",
        ],
        "dev": [
            "black",
            "flake8",
            "mypy",
            "pre-commit",
        ],
    },
    entry_points={
        "console_scripts": [
            "fhir-ingestion=fhir_ingestion.entrypoints.fhir_api:app",
            "lab-dp-processor=lab_dp.entrypoints.event_processor:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
    ],
)