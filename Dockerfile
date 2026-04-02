FROM python:3.11-slim

WORKDIR /app

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DLR_HEADLESS=1 \
    DEBIAN_FRONTEND=noninteractive \
    FFMPEG_STATIC_URL=https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz

COPY . /app

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
    retry 5 apt-get install -y --no-install-recommends tzdata xz-utils && \
    retry 5 curl -fL --http1.1 --retry 10 --retry-delay 5 --retry-all-errors "$FFMPEG_STATIC_URL" -o /tmp/ffmpeg-static.tar.xz && \
    mkdir -p /tmp/ffmpeg-static && \
    tar -xJf /tmp/ffmpeg-static.tar.xz -C /tmp/ffmpeg-static --strip-components=1 && \
    install -m 755 /tmp/ffmpeg-static/ffmpeg /usr/local/bin/ffmpeg && \
    if [ -f /tmp/ffmpeg-static/ffprobe ]; then install -m 755 /tmp/ffmpeg-static/ffprobe /usr/local/bin/ffprobe; fi && \
    ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/ffmpeg-static /tmp/ffmpeg-static.tar.xz

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python", "-m", "client.infra.docker.healthcheck"]

CMD ["python", "main.py"]
