# hackathon

Backend:

    cd backend
    mvn clean package
    mvn verify -Pserve-backend

Frontend:

    cd frontend
    npm install --legacy-peer-deps
    npm run build
    ng serve

Parent

    mvn clean package - build all

Podman/Docker

    podman machine rm
    podman machine init
    podman machine start
    podman image list
    podman container list

    podman stop $(podman ps -a -q)
    podman rmi -f $(podman images -a -q)

    cd backend
    podman build -t backend-app -f Dockerfile .

    podman image list

    podman run -i --rm -p 8080:8080 backend-app
    
    podman container list

    cd ../frontend
    podman build -t frontend-app -f Dockerfile .

    podman image list

    podman run -i --rm -p 4200:80 frontend-app

    podman container list
    
    podman stop $(podman ps -a -q)
    podman rmi -f $(podman images -a -q)

Kubernetes:

Attention: Everything from here works with docker only
because minikube --driver=podman does not work on MacOS
so far

    minikube start --driver=docker
    minikube dashboard &

to get the container images in the isolated Docker daemon
of Minikube

go to terminal and switch

    eval $(minikube docker-env)

do docker build ... for backend/frontend

    docker images
    docker ps -a

switch back to original terminal with

    eval $(minikube docker-env --unset)

Then do the deployment

    kubectl apply -f k8s/backend-deployment.yaml
    kubectl apply -f k8s/backend-service.yaml
    kubectl apply -f k8s/frontend-deployment.yaml
    kubectl apply -f k8s/frontend-service.yaml
    minikube service frontend

Hints:

    docker build --no-cache -t frontend-app -f Dockerfile .

Check daemon

    docker info

If not running

    export DOCKER_HOST=unix:///var/run/docker.sock

Finally

    minikube delete

NodePort:

frontend-service:

apiVersion: v1
kind: Service
metadata:
name: frontend
spec:
selector:
app: frontend
ports:
- protocol: TCP
port: 80
targetPort: 80
type: NodePort