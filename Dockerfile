FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    EC_DATA_DIR=/tmp/ec-data \
    EC_PROFILES_ROOT=/tmp/ec-data \
    EC_HEADLESS=1 \
    EC_REMOTE_MODE=1 \
    EC_PUBLIC_SESSIONS=1 \
    EC_PUBLIC_MAX_SESSIONS=3 \
    EC_PUBLIC_URL=https://englishcentral-studio.onrender.com

WORKDIR /tmp/build
RUN apt-get update && apt-get install -y --no-install-recommends unzip ca-certificates libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Build from the complete original V18.13.3 archive. No feature-reduced source tree.
COPY EnglishCentral-Studio-18.13.3-G0DMOD3.zip /tmp/englishcentral.zip
RUN mkdir -p /app && unzip -q /tmp/englishcentral.zip -d /tmp/unpacked \
    && cp -a /tmp/unpacked/EnglishCentral-Studio/. /app/ \
    && rm -rf /tmp/unpacked /tmp/englishcentral.zip

# Server-side isolation for each public visitor.
COPY install_public_gateway.py /tmp/install_public_gateway.py
# Browser-side bridge: hosted UI uses the local Windows connector only after explicit approval.
COPY enable_pc_bridge_cloud.py /tmp/enable_pc_bridge_cloud.py
COPY install_pc_download_link.py /tmp/install_pc_download_link.py
RUN EC_SOURCE_ROOT=/app python /tmp/install_public_gateway.py \
    && EC_SOURCE_ROOT=/app python /tmp/enable_pc_bridge_cloud.py \
    && python /tmp/install_pc_download_link.py \
    && python -m py_compile /app/servidor.py /app/mobile_app.py /app/perfis.py

WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium \
    && apt-get update \
    && apt-get install -y --no-install-recommends espeak-ng xvfb xauth \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 ecstudio \
    && mkdir -p /tmp/ec-data \
    && chown -R ecstudio:ecstudio /tmp/ec-data

USER 10001:10001
EXPOSE 8765
CMD ["sh", "-c", "exec python servidor.py --host 0.0.0.0 --port ${PORT:-8765}"]
