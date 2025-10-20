# hackathon

Backend:

    cd backend
    mvn clean package
    mvn verify -Pserve-backend

Frontend:

    cd frontend
    mvn clean package
    mvn frontend:npm -Dfrontend.npm.arguments=start

Parent

    mvn clean package - build all

Docker

    cd backend
    docker build -t backend-app -f Dockerfile .