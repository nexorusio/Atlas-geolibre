# syntax=docker/dockerfile:1
FROM node:26.10.0-alpine AS build
RUN apk add --no-cache git python3
RUN git clone --depth 1 --branch v1.22.0 https://github.com/geolens-io/geolens.git /source \
    && test "$(git -C /source rev-parse HEAD)" = "40b8473cf7506a44cd6f52201366d41d19b44f3a"
COPY deploy/geolens-branding/ /branding/
COPY apps/geolibre-desktop/public/nexorus-wordmark.png /branding/assets/nexorus-wordmark.png
COPY apps/geolibre-desktop/public/nexorus-icon.png /branding/assets/nexorus-icon.png
COPY apps/geolibre-desktop/public/favicon.png /branding/assets/favicon.png
COPY apps/geolibre-desktop/public/apple-touch-icon.png /branding/assets/apple-touch-icon.png
COPY apps/geolibre-desktop/public/pwa-192x192.png /branding/assets/pwa-192x192.png
COPY apps/geolibre-desktop/public/pwa-512x512.png /branding/assets/pwa-512x512.png
RUN python3 /branding/apply.py /source/frontend
WORKDIR /source/frontend
RUN --mount=type=cache,target=/root/.npm npm ci --prefer-offline
RUN npm run build && npm run lint && npm run typecheck && npm run test:coverage

FROM ghcr.io/geolens-io/geolens-frontend:1.22.0
USER root
COPY --from=build --chown=nginx:nginx /source/frontend/dist /opt/geolens/html
COPY --from=build --chown=nginx:nginx /source/frontend/public/env-config.template.js /opt/geolens/html/env-config.template.js
COPY --from=build /source/LICENSE /usr/share/licenses/atlas-catalog/LICENSE
COPY --from=build /source/NOTICE /usr/share/licenses/atlas-catalog/NOTICE
LABEL org.opencontainers.image.title="Nexorus Atlas Catalog" \
      org.opencontainers.image.source="https://github.com/nexorusio/Atlas-geolibre" \
      org.opencontainers.image.licenses="Apache-2.0"
USER nginx
