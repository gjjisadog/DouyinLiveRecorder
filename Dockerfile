FROM python:3.11.9-slim-bookworm AS runtime

ARG VERSION=4.0.7
ARG REVISION=unknown
ARG CREATED=unknown

LABEL org.opencontainers.image.title="Douyin Live Recorder" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}" \
      org.opencontainers.image.created="${CREATED}" \
      org.opencontainers.image.source="https://github.com/gjjisadog/DouyinLiveRecorder"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Shanghai

WORKDIR /app

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o Acquire::Retries=5 update \
    && apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        nodejs \
        tini \
        tzdata \
    && ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV DLR_DISABLE_FILE_LOGS=1

ARG TARGETARCH
COPY requirements.lock /app/requirements.lock
RUN if [ "$TARGETARCH" = "arm" ]; then \
        apt-get -o Acquire::Retries=5 update \
        && apt-get -o Acquire::Retries=5 install -y --no-install-recommends build-essential; \
    fi \
    && python -m pip install --no-cache-dir -r /app/requirements.lock \
    && if [ "$TARGETARCH" = "arm" ]; then \
        apt-get purge -y --auto-remove build-essential; \
    fi \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=10001:10001 . /app

RUN groupadd --gid 10001 recorder \
    && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin recorder \
    && mkdir -p /data/downloads /data/state /app/config /app/logs /app/backup_config \
    && chown -R 10001:10001 /data /app

USER 10001:10001

ENTRYPOINT ["/usr/bin/tini", "--"]

FROM runtime AS daemon

ENV DOUYIN_CONFIG=/app/config/douyin.yaml

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["python", "-m", "app.health", "check"]

CMD ["python", "-m", "app.douyin_daemon"]

FROM runtime AS nas-web

ENV DOUYIN_CONFIG=/app/config/douyin.yaml \
    DLR_WEB_LOG_DIR=/app/logs \
    DLR_STATE_PATH=/data/state \
    DLR_WEB_HOST=0.0.0.0 \
    DLR_WEB_PORT=18091 \
    DLR_WEB_TOKEN_FILE=/run/secrets/web_token \
    DLR_HEALTHCHECK_WEB_URL=http://127.0.0.1:18091/health

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["python", "-m", "client.infra.docker.healthcheck"]

CMD ["python", "-m", "client.infra.docker.launcher"]
