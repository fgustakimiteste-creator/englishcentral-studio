FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    EC_DATA_DIR=/tmp/ec-data \
    EC_PROFILES_ROOT=/tmp/ec-data \
    EC_REMOTE_MODE=1 \
    EC_PUBLIC_URL=https://englishcentral-studio.onrender.com \
    EC_PUBLIC_SESSIONS=1

WORKDIR /tmp/build
RUN apt-get update && apt-get install -y --no-install-recommends unzip ca-certificates libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Extract the exact V18.13.5 project. The source archive and SKILL.md remain untouched.
COPY EnglishCentral-Studio-18.13.5-G0DMOD3.zip /tmp/englishcentral.zip
RUN mkdir -p /app && unzip -q /tmp/englishcentral.zip -d /tmp/unpacked \
    && cp -a /tmp/unpacked/EnglishCentral-Studio/. /app/ \
    && rm -rf /tmp/unpacked /tmp/englishcentral.zip

# Only the automatic private-session/token patch is applied to the original project.
COPY install_private_auto_token.py /tmp/install_private_auto_token.py
RUN EC_SOURCE_ROOT=/app python /tmp/install_private_auto_token.py \
    && python -m py_compile /app/servidor.py /app/mobile_app.py /app/perfis.py

WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt \
    && mkdir -p /tmp/ec-data \
    && useradd --create-home --uid 10001 ecstudio \
    && chown -R ecstudio:ecstudio /tmp/ec-data

USER 10001:10001
EXPOSE 10000
CMD ["sh", "-c", "exec python servidor.py --host 0.0.0.0 --port ${PORT:-10000}"]
