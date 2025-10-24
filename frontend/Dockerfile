# -------- Stage 1: Build the Angular app --------
FROM node:18 AS build
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install --legacy-peer-deps

# Copy the rest of the app
COPY . .

# Build Angular app (outputs to /app/dist)
RUN npm run build --configuration=production

# -------- Stage 2: Serve with nginx --------
FROM nginx:alpine
WORKDIR /usr/share/nginx/html

# Remove default nginx site content
RUN rm -rf ./*

# ✅ Copy build result from previous stage
COPY --from=build /app/dist/ /usr/share/nginx/html/

# Replace default nginx config
# COPY --from=build /app/nginx/default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]