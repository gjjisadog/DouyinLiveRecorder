FROM python:3.11-slim

WORKDIR /app

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DLR_HEADLESS=1 \
    DEBIAN_FRONTEND=noninteractive

COPY requirements.docker.txt /app/requirements.docker.txt

RUN retry() { \
        local attempts="$1"; shift; \
        local index=1; \
        until "$@"; do \
            if [ "${index}" -ge "${attempts}" ]; then \
                return 1; \
            fi; \
            index=$((index + 1)); \
            sleep 5; \
        done; \
    }; \
    retry 5 apt-get update && \
    retry 5 apt-get install -y --no-install-recommends curl gnupg ca-certificates && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    retry 5 apt-get update && \
    retry 5 apt-get install -y --no-install-recommends nodejs

RUN pip install -r requirements.docker.txt

RUN retry() { \
        local attempts="$1"; shift; \
        local index=1; \
        until "$@"; do \
            if [ "${index}" -ge "${attempts}" ]; then \
                return 1; \
            fi; \
            index=$((index + 1)); \
            sleep 5; \
        done; \
    }; \
    retry 5 apt-get update && \
    retry 5 apt-get install -y --no-install-recommends tzdata ffmpeg && \
    ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . /app

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python", "-m", "client.infra.docker.healthcheck"]

EXPOSE 18091

CMD ["python", "-m", "client.infra.docker.launcher"]
