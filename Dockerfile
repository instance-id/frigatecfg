FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/
COPY static/ ./static/
RUN uv pip install --system --no-cache .

ENV PYTHONPATH=/app/src
ENV FLASK_APP=frigatecfg.app
ENV FRIGATE_CONFIG_PATH=/config/config.yml
ENV FRIGATE_CONTAINER_NAME=frigate
ENV FRIGATE_DOCKER_HOST=unix:///var/run/docker.sock

EXPOSE 8080

CMD ["python", "-m", "frigatecfg.app"]
