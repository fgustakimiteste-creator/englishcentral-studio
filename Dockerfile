FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
    EC_DATA_DIR=/tmp/ec-data \
    EC_PROFILES_ROOT=/tmp/ec-data \
    EC_HEADLESS=1

WORKDIR /tmp/build
RUN apt-get update && apt-get install -y --no-install-recommends unzip ca-certificates libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY EnglishCentral-Studio-18.13.3-G0DMOD3.zip /tmp/englishcentral.zip
RUN mkdir -p /app && unzip -q /tmp/englishcentral.zip -d /tmp/unpacked \
    && cp -a /tmp/unpacked/EnglishCentral-Studio/. /app/ \
    && rm -rf /tmp/unpacked /tmp/englishcentral.zip

COPY enable_public_sessions.py /tmp/enable_public_sessions.py
COPY fix_public_ui.py /tmp/fix_public_ui.py
COPY fix_public_home.py /tmp/fix_public_home.py
RUN python /tmp/enable_public_sessions.py && python /tmp/fix_public_ui.py && python /tmp/fix_public_home.py

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
