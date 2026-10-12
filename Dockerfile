FROM node:22-bookworm-slim AS assets
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY tailwind.config.js ./
COPY templates ./templates
COPY static ./static
COPY scripts/build-ui.cjs ./scripts/build-ui.cjs
RUN npm run build:css

FROM python:3.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production
WORKDIR /app
COPY requirements-runtime.txt requirements-production.txt ./
RUN pip install --no-cache-dir -r requirements-production.txt && useradd --create-home app
COPY --chown=app:app . .
COPY --from=assets --chown=app:app /build/static/css/ui.css ./static/css/ui.css
COPY --from=assets --chown=app:app /build/static/js/alpine.min.js ./static/js/alpine.min.js
RUN mkdir -p /app/instance && chown app:app /app/instance
USER app
EXPOSE 8000
CMD ["python", "-m", "services.servidor"]
