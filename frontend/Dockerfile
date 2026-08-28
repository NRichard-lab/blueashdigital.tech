FROM node:22-alpine AS build
WORKDIR /app
ARG DEPLOYMENT_VERSION=local
ARG VITE_API_BASE_URL
ARG VITE_RADAR_PUBLIC_ORIGIN=https://radar.blueashdigital.tech
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_RADAR_PUBLIC_ORIGIN=$VITE_RADAR_PUBLIC_ORIGIN
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm test && npm run build

FROM nginx:1.27-alpine
ARG DEPLOYMENT_VERSION=local
LABEL org.opencontainers.image.revision=$DEPLOYMENT_VERSION
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80

