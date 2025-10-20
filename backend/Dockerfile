# ----------- Build stage ----------- #
FROM maven:3.9.6-eclipse-temurin-21 AS build

WORKDIR /app/backend

COPY pom.xml .
RUN mvn dependency:go-offline

COPY src src
RUN mvn package -Dmaven.test.skip=true

# ----------- Runtime stage ----------- #
FROM eclipse-temurin:21-jre-ubi9-minimal

WORKDIR /app/backend
COPY --from=build /app/backend/target/*.jar personservice.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "personservice.jar"]

