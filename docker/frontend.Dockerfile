# Step 1: Build React Application
FROM node:20-slim AS build-stage

WORKDIR /app

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Step 2: Serve using Nginx
FROM nginx:alpine

COPY --from=build-stage /app/dist /usr/share/nginx/html
# COPY custom Nginx configuration if required, otherwise default works.
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
