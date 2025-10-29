docker rmi -f $(docker images -a -q)

docker-compose up redis
docker-compose up minio
docker-compose up fhir-api

docker compose --profile test run --rm tests

localhost:9001   minioadmin/minioadmin123

---

redis observation:
docker exec -it 7d91da86a645 sh
redis-cli -h localhost -p 6379
INFO
PUBSUB CHANNELS
MONITOR
