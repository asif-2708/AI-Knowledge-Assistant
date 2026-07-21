# Stage 1: Build Angular application
FROM node:20-alpine AS build

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json ./

# Install npm dependencies
RUN npm ci --legacy-peer-deps

# Copy application source code
COPY . .

# Build production Angular bundle
RUN npm run build -- --configuration production

# Stage 2: Serve application with Nginx
FROM nginx:alpine

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy production build outputs
COPY --from=build /app/dist/frontend /usr/share/nginx/html

# Expose HTTP port 80
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
