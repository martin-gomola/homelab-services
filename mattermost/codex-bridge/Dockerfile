FROM python:3.12-slim

ARG CODEX_VERSION=0.105.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/home/codex

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates nodejs npm \
    && npm install -g "@openai/codex@${CODEX_VERSION}" \
    && npm cache clean --force \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 -s /bin/bash codex \
    && mkdir -p /home/codex/.codex /tmp/codex-bridge \
    && chown -R codex:codex /home/codex /tmp/codex-bridge

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install -r requirements.txt

COPY --chown=codex:codex app.py .
COPY --chown=codex:codex codex_bridge ./codex_bridge

USER codex

EXPOSE 8092

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8092"]
