FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @openai/codex@0.104.0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

RUN useradd -m -u 1000 -s /bin/bash codex \
    && mkdir -p /var/lib/codex-gateway /home/codex/.codex \
    && chown -R codex:codex /var/lib/codex-gateway /home/codex /app

USER codex
ENV HOME=/home/codex

EXPOSE 8091

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8091"]
