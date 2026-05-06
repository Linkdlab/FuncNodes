# Running FuncNodes with Docker

FuncNodes publishes Docker images to GitHub Container Registry:

```text
ghcr.io/linkdlab/funcnodes
```

Use Docker when you want to run the FuncNodes web UI and worker manager without installing Python packages on the host.

## Pull the Image

Use `latest` for the newest release:

```bash
docker pull ghcr.io/linkdlab/funcnodes:latest
```

Use a version tag for reproducible deployments:

```bash
docker pull ghcr.io/linkdlab/funcnodes:v1.6.0
```

## Run with Docker

Create a local configuration directory first. This keeps workers, settings, and runtime state outside the container:

```bash
mkdir -p funcnodes_config
```

Start FuncNodes:

```bash
docker run --rm \
  -p 8000:8000 \
  -p 9380:9380 \
  -p 9382-9482:9382-9482 \
  -e FUNCNODES_RUNSERVER_HOST=0.0.0.0 \
  -e FUNCNODES_RUNSERVER_PORT=8000 \
  -e FUNCNODES_WORKER_MANAGER_HOST=0.0.0.0 \
  -e FUNCNODES_WORKER_MANAGER_PORT=9380 \
  -e FUNCNODES_HOST=0.0.0.0 \
  -e FUNCNODES_WS_WORKER_STARTPORT=9382 \
  -v ./funcnodes_config:/usr/local/app/.funcnodes \
  ghcr.io/linkdlab/funcnodes:latest
```

Open the UI at:

```text
http://localhost:8000
```

The worker manager listens on port `9380`. Worker websocket ports use the exposed range `9382-9482`.

## Run with Docker Compose

Use this `docker-compose.yaml`:

```yaml
services:
  funcnodes:
    image: ghcr.io/linkdlab/funcnodes:latest
    ports:
      - "8000:8000"
      - "9380:9380"
      - "9382-9482:9382-9482"
    environment:
      FUNCNODES_RUNSERVER_HOST: "0.0.0.0"
      FUNCNODES_RUNSERVER_PORT: "8000"
      FUNCNODES_WORKER_MANAGER_HOST: "0.0.0.0"
      FUNCNODES_WORKER_MANAGER_PORT: "9380"
      FUNCNODES_HOST: "0.0.0.0"
      FUNCNODES_WS_WORKER_STARTPORT: "9382"
    volumes:
      - ./funcnodes_config:/usr/local/app/.funcnodes
```

Start the service:

```bash
mkdir -p funcnodes_config
docker compose up
```

Run in the background:

```bash
docker compose up -d
```

Stop the service:

```bash
docker compose down
```

To pin a release, change the image tag:

```yaml
image: ghcr.io/linkdlab/funcnodes:v1.6.0
```

You can also download the example file: [docker-compose.yaml](https://linkdlab.github.io/FuncNodes/v1.6.0/examples/docker-compose.yaml).

## Configuration Volume

The container uses:

```text
FUNCNODES_CONFIG_DIR=/usr/local/app/.funcnodes
```

Mounting `./funcnodes_config` to that path makes worker configuration persistent across container restarts. Do not mount this directory read-only.

## Updating

For `latest`, pull the newest image and restart:

```bash
docker compose pull
docker compose up -d
```

For pinned deployments, edit the image tag in `docker-compose.yaml`, then run the same commands.
