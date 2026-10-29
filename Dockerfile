# Council 10930 image: built Vite site, static /images, and the FastAPI app.
#
# Build args (baked at image build, not read from a k3s Secret):
#   VITE_API_BASE   Browser API origin. Leave empty so the site calls same-origin /api.
#                   Do not pass tokens, database URLs, or other secrets as build args.
#
# Runtime env (injected by the k3s Secret and ConfigMap; the app reads these
# from the process environment in backend/config.py):
#   DATABASE_URL or POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB
#   JWT_SECRET
#   REDIS_URL, REDIS_MAXMEMORY, REDIS_MAXMEMORY_POLICY
#   COOKIE_SECURE, COOKIE_SAMESITE, CORS_ORIGINS, CORS_ORIGIN_REGEX
#   UPLOAD_DIR
#   MAIL_ENABLED, MAIL_FROM, CLOUDFLARE_EMAIL_TOKEN
#   CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_ZONE_ID, CLOUDFLARE_ROUTING_DOMAIN
# API_PROXY_TARGET is only for the Vite dev server and is not used here.

FROM node:22-bookworm-slim AS frontend
WORKDIR /src/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
COPY css/ /src/css/
ARG VITE_API_BASE=
ENV VITE_API_BASE=${VITE_API_BASE}
RUN npm run build

FROM python:3.12-slim-bookworm AS runtime
RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 1000 --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app /data/uploads /tmp/nginx/client /tmp/nginx/proxy /tmp/nginx/fastcgi /tmp/nginx/uwsgi /tmp/nginx/scgi \
    && chown -R app:app /app /data/uploads /tmp/nginx

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/ /app/backend/
COPY images/ /app/images/
COPY logo_email_example.png /app/logo_email_example.png
COPY --from=frontend /src/frontend/dist /app/frontend/dist
COPY docker/nginx.conf /app/docker/nginx.conf
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
RUN chmod 755 /app/docker/entrypoint.sh \
    && chown -R app:app /app

USER 1000:1000
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
ENTRYPOINT ["/app/docker/entrypoint.sh"]
