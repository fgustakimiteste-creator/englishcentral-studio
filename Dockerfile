FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EC_DATA_DIR=/tmp/ec-data \
    EC_PROFILES_ROOT=/tmp/ec-data

WORKDIR /tmp/build
RUN apt-get update && apt-get install -y --no-install-recommends unzip ca-certificates libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Preserve and serve the exact full original V18.13.3 project.
COPY EnglishCentral-Studio-18.13.3-G0DMOD3.zip /tmp/englishcentral.zip
RUN mkdir -p /app && unzip -q /tmp/englishcentral.zip -d /tmp/unpacked \
    && cp -a /tmp/unpacked/EnglishCentral-Studio/. /app/ \
    && rm -rf /tmp/unpacked /tmp/englishcentral.zip

# Install only the Windows-to-local-Chrome connector. No fake cloud browser/session.
COPY install_windows_bridge.py /tmp/install_windows_bridge.py
RUN EC_SOURCE_ROOT=/app python /tmp/install_windows_bridge.py \
    && python -m py_compile /app/servidor.py /app/mobile_app.py /app/iniciar.py

WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /tmp/ec-data \
    && useradd --create-home --uid 10001 ecstudio \
    && chown -R ecstudio:ecstudio /tmp/ec-data

USER 10001:10001
EXPOSE 10000
CMD ["sh", "-c", "exec python servidor.py --host 0.0.0.0 --port ${PORT:-10000}"]
