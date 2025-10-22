docker rmi -f $(docker images -a -q)

docker-compose up redis
docker-compose up minio
docker-compose up fhir-api

docker compose --profile test run --rm tests

localhost:9001   minioadmin/minioadmin123