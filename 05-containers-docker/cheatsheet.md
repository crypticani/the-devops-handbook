# Module 05: Containers & Docker — Cheat Sheet

> Command reference for Docker and Compose. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [Images](#images) · [Containers](#containers) · [Inspect & debug](#inspecting--debugging) · [Dockerfile](#dockerfile-reference) · [Build](#building) · [Networking](#networking) · [Volumes](#volumes--storage) · [Compose](#docker-compose) · [Registry](#registries) · [Cleanup](#cleanup--disk) · [Security](#security) · [Errors](#error-decoder)

---

## Images

```bash
docker pull nginx:1.25                 # always pin a tag, never rely on :latest
docker pull --platform linux/amd64 nginx:1.25    # cross-arch on Apple Silicon
docker images                          # or: docker image ls
docker images --format '{{.Repository}}:{{.Tag}}\t{{.Size}}' | column -t
docker history nginx:1.25              # ⭐ layer-by-layer size breakdown
docker history --no-trunc myapp:v1     # full commands per layer
docker inspect nginx:1.25
docker tag myapp:v1 ghcr.io/org/myapp:v1
docker rmi nginx:1.25
docker save myapp:v1 | gzip > myapp.tar.gz     # export for air-gapped transfer
docker load < myapp.tar.gz
docker image prune          # dangling images
docker image prune -a       # ⚠️ everything not used by a container
```

**Image naming**: `[registry/][namespace/]repository[:tag|@sha256:digest]`

```
docker.io/library/nginx:1.25          # Docker Hub official
ghcr.io/myorg/myapp:v2.1.0            # GitHub Container Registry
123456789012.dkr.ecr.us-east-1.amazonaws.com/myapp:v1    # AWS ECR
myapp@sha256:abc123...                # ⭐ immutable — a digest can never be re-pushed
```

---

## Containers

```bash
docker run nginx:1.25                             # foreground
docker run -d --name web nginx:1.25               # detached, named
docker run -d -p 8080:80 --name web nginx:1.25    # host:container port
docker run -p 127.0.0.1:8080:80 nginx             # bind to localhost only ⭐
docker run --rm -it alpine sh                     # throwaway interactive shell
docker run -e KEY=value -e OTHER=x myapp
docker run --env-file .env myapp
docker run -v mydata:/data myapp                  # named volume
docker run -v "$PWD":/app:ro myapp                # bind mount, read-only
docker run --network mynet myapp
docker run --restart unless-stopped myapp
docker run -u 1000:1000 myapp                     # run as a specific UID:GID
docker run -w /app myapp                          # working directory
docker run --memory 512m --cpus 1.5 myapp         # ⭐ always set limits
docker run --read-only --tmpfs /tmp myapp         # immutable root filesystem
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE myapp
docker run --health-cmd 'curl -f localhost/ || exit 1' --health-interval 30s myapp

docker ps                          # running only
docker ps -a                       # ⭐ INCLUDING exited — where crashed containers hide
docker ps -q                       # IDs only (for scripting)
docker ps --filter status=exited --filter name=web
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

docker start|stop|restart web
docker stop -t 30 web              # give it 30s before SIGKILL
docker kill web                    # SIGKILL immediately
docker kill -s HUP web             # send a specific signal
docker pause|unpause web
docker rm web
docker rm -f web                   # stop and remove
docker rename web web-old
docker update --memory 1g web      # change limits on a running container
docker wait web                    # block until it exits, print its exit code
```

---

## Inspecting & Debugging

```bash
docker logs web
docker logs -f web                        # follow
docker logs --tail 100 -f web
docker logs --since 10m web
docker logs --timestamps web
docker logs web 2>&1 | grep -i error

docker exec -it web bash                  # shell into a RUNNING container
docker exec -it web sh                    # alpine/distroless often lack bash
docker exec -u root -it web bash          # as root even if the container runs as a user
docker exec web env                       # its environment variables
docker exec web ps aux                    # its processes

docker inspect web                                            # everything, as JSON
docker inspect -f '{{.State.Status}}' web
docker inspect -f '{{.State.ExitCode}}' web                   # ⭐ why it died
docker inspect -f '{{.State.OOMKilled}}' web                  # ⭐ was it OOM-killed?
docker inspect -f '{{json .State.Health}}' web | jq
docker inspect -f '{{.NetworkSettings.IPAddress}}' web
docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{$v.IPAddress}}{{end}}' web
docker inspect -f '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{"\n"}}{{end}}' web
docker inspect -f '{{.Config.Cmd}} {{.Config.Entrypoint}}' web

docker stats                              # live CPU/memory/network for all containers
docker stats --no-stream                  # one snapshot (scriptable)
docker top web                            # processes, as seen from the host
docker diff web                           # ⭐ files changed since the image was built
docker port web                           # published port mappings
docker events --since 10m                 # daemon event stream — restarts, OOM kills
docker cp web:/etc/nginx/nginx.conf ./    # copy out
docker cp ./index.html web:/usr/share/nginx/html/

# Debug a container with no shell (distroless/scratch)
docker run --rm -it --pid container:web --network container:web \
  --cap-add SYS_PTRACE nicolaka/netshoot
```

**Debugging a crash loop:**

```bash
docker ps -a                                        # 1. find it and read the exit code
docker logs --tail 50 web                           # 2. what did it say before dying?
docker inspect -f '{{.State.ExitCode}} OOM={{.State.OOMKilled}}' web    # 3. how did it die?
docker run --rm -it --entrypoint sh myapp:v1        # 4. ⭐ override the entrypoint and look around
docker run --rm myapp:v1 ls -la /app                # 5. is the artifact even in the image?
```

---

## Dockerfile Reference

| Instruction | Purpose | Gotcha |
|-------------|---------|--------|
| `FROM image:tag` | Base image | Pin the tag. Use a digest for reproducibility |
| `WORKDIR /app` | Set + create the working directory | Use this, never `RUN cd` |
| `COPY src dst` | Copy from build context | Prefer over `ADD` |
| `ADD` | Copy + auto-extract archives + fetch URLs | Surprising behaviour — avoid unless extracting a tarball |
| `RUN cmd` | Execute at **build** time | Each `RUN` is a layer; chain with `&&` |
| `CMD ["a","b"]` | Default command, **overridable** | Exec form only |
| `ENTRYPOINT ["a"]` | The fixed executable | `CMD` becomes its default arguments |
| `ENV K=V` | Environment variable, build **and** run | Visible in `docker inspect` — never secrets |
| `ARG K=V` | Build-time variable only | Visible in `docker history` — never secrets |
| `EXPOSE 8080` | Documentation only | Does **not** publish; you still need `-p` |
| `USER appuser` | Drop privileges | Put it after the installs |
| `VOLUME /data` | Declare a mount point | Creates an anonymous volume if not overridden |
| `HEALTHCHECK` | Container-level health probe | Compose and Swarm use it; Kubernetes ignores it |
| `LABEL k=v` | Metadata | Use OCI standard labels |
| `ONBUILD` | Trigger for child images | Confusing — avoid |
| `STOPSIGNAL SIGTERM` | Signal sent on stop | |

### Production Dockerfile

```dockerfile
# syntax=docker/dockerfile:1

########## Stage 1: build ##########
FROM node:20-slim AS builder
WORKDIR /app

# Dependencies FIRST — this layer caches across source changes ⭐
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY . .
RUN npm run build && npm prune --omit=dev

########## Stage 2: runtime ##########
FROM node:20-slim AS runtime

ENV NODE_ENV=production \
    PORT=8080

RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app
COPY --from=builder --chown=app:app /app/node_modules ./node_modules
COPY --from=builder --chown=app:app /app/dist ./dist

USER app
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD node -e "require('http').get('http://127.0.0.1:8080/health',r=>process.exit(r.statusCode===200?0:1)).on('error',()=>process.exit(1))"

ENTRYPOINT ["node"]
CMD ["dist/server.js"]
```

### `CMD` vs `ENTRYPOINT`

```dockerfile
CMD ["nginx", "-g", "daemon off;"]      # docker run img echo hi  → runs "echo hi"
ENTRYPOINT ["nginx"]                    # docker run img -v       → runs "nginx -v"
ENTRYPOINT ["nginx"]                    # combined: default args that users can replace
CMD ["-g", "daemon off;"]
```

> ⚠️ Use the **exec form** (`["cmd","arg"]`), not the shell form (`cmd arg`). Shell form wraps your process in `/bin/sh -c`, which becomes PID 1 and **does not forward SIGTERM** — your container then takes the full 10-second timeout to die and never runs its graceful shutdown.

### `.dockerignore`

```gitignore
.git
.github
node_modules
__pycache__
*.pyc
.venv
dist
build
*.log
.env
.env.*
*.pem
*.key
Dockerfile*
docker-compose*.yml
.terraform
README.md
```

> 💡 `.dockerignore` does two jobs: it shrinks the build context (faster builds) and it stops `COPY . .` silently baking `.git`, `.env`, and credentials into your image.

---

## Building

```bash
docker build -t myapp:v1 .
docker build -t myapp:v1 -f docker/Dockerfile.prod .
docker build --target builder -t myapp:debug .        # ⭐ build one stage only
docker build --no-cache -t myapp:v1 .
docker build --pull -t myapp:v1 .                     # refresh the base image
docker build --build-arg VERSION=1.2.3 -t myapp:v1 .
docker build --progress=plain -t myapp:v1 .           # full log output, no collapsing
docker build -t myapp:v1 -t myapp:latest .            # multiple tags

# BuildKit secrets — never bake credentials into a layer
DOCKER_BUILDKIT=1 docker build --secret id=npmrc,src=$HOME/.npmrc -t myapp .
# In the Dockerfile:
#   RUN --mount=type=secret,id=npmrc,target=/root/.npmrc npm ci

# Multi-architecture
docker buildx create --use --name multi
docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/org/app:v1 --push .

docker builder prune                    # clear the build cache
docker system df                        # ⭐ where is my disk going?
```

---

## Networking

```bash
docker network ls
docker network create myapp-net
docker network create --driver bridge --subnet 172.28.0.0/16 mynet
docker network inspect myapp-net
docker network connect myapp-net web
docker network disconnect myapp-net web
docker network prune
```

| Driver | Behaviour |
|--------|-----------|
| `bridge` (default) | Private network on the host. **User-defined bridges get DNS by container name** |
| `host` | No isolation — the container uses the host's network stack directly (Linux only) |
| `none` | No networking at all |
| `overlay` | Multi-host (Swarm) |
| `macvlan` | Container gets its own MAC/IP on the physical LAN |

```bash
# Containers reach each other by NAME on a user-defined network
docker network create appnet
docker run -d --name db     --network appnet postgres:15
docker run -d --name api    --network appnet -e DB_HOST=db myapi
# Inside 'api': postgres://db:5432   ← the container name, not localhost

# From a container, reach a service on the HOST
--add-host=host.docker.internal:host-gateway    # Linux; built in on Mac/Windows
```

> 💡 Three rules that resolve most container networking confusion:
> **(1)** `localhost` inside a container means *that container*, never the host or a sibling.
> **(2)** `-p 8080:80` is only for traffic entering from **outside** Docker; containers on a shared network talk directly on the container port with no publishing needed.
> **(3)** The **default** bridge has no DNS. Always `docker network create` your own (Compose does this automatically).

---

## Volumes & Storage

```bash
docker volume create mydata
docker volume ls
docker volume inspect mydata            # shows the real path under /var/lib/docker
docker volume rm mydata
docker volume prune                     # ⚠️ deletes all unused volumes

docker run -v mydata:/var/lib/postgresql/data postgres:15    # named volume
docker run -v "$PWD/config":/etc/app:ro myapp                # bind mount, read-only
docker run --mount type=bind,src="$PWD",dst=/app,readonly myapp   # explicit syntax
docker run --tmpfs /tmp:size=100m myapp                      # in-memory, never persisted

# Back up a volume
docker run --rm -v mydata:/data -v "$PWD":/backup alpine \
  tar czf /backup/mydata-$(date +%F).tar.gz -C /data .

# Restore
docker run --rm -v mydata:/data -v "$PWD":/backup alpine \
  sh -c 'cd /data && tar xzf /backup/mydata-2026-08-04.tar.gz'
```

| Type | Managed by | Use for |
|------|-----------|---------|
| **Named volume** | Docker | Databases, anything that must persist. Portable, backed up as a unit |
| **Bind mount** | You | Source code in development, host config files |
| **tmpfs** | Kernel (RAM) | Secrets and scratch data that must never touch disk |

---

## Docker Compose

```bash
docker compose up -d                    # ⭐ 'docker compose' (v2), not 'docker-compose'
docker compose up -d --build            # rebuild images first
docker compose up -d --force-recreate
docker compose down                     # stop and remove containers + networks
docker compose down -v                  # ⚠️ also delete volumes (data loss)
docker compose ps
docker compose logs -f
docker compose logs -f api              # one service
docker compose exec api sh
docker compose run --rm api npm test    # one-off task container
docker compose restart api
docker compose stop / start
docker compose build --no-cache
docker compose pull
docker compose config                   # ⭐ show the fully resolved config (validates it)
docker compose top
docker compose --profile debug up -d    # opt-in services
docker compose -f base.yml -f prod.yml up -d       # layered overrides
```

```yaml
# compose.yaml
services:
  api:
    build:
      context: .
      target: runtime
    image: myapp:local
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:8080"
    environment:
      DATABASE_URL: postgres://app:${DB_PASSWORD:?set DB_PASSWORD}@db:5432/app
      LOG_LEVEL: ${LOG_LEVEL:-info}
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy      # ⭐ wait for the healthcheck, not just startup
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8080/health"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 20s
    deploy:
      resources:
        limits: {cpus: "1.0", memory: 512M}
    user: "1000:1000"
    read_only: true
    tmpfs: [/tmp]
    security_opt: ["no-new-privileges:true"]
    cap_drop: [ALL]
    logging:
      driver: json-file
      options: {max-size: "10m", max-file: "3"}

  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: app
      POSTGRES_DB: app
      POSTGRES_PASSWORD: ${DB_PASSWORD:?set DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

> 💡 `depends_on` **without** `condition: service_healthy` only waits for the container to *start*, not to be *ready*. That's the cause of the classic "my app can't reach Postgres on the first run" bug.

---

## Registries

```bash
docker login ghcr.io -u USERNAME                          # prompts for a token
echo "$TOKEN" | docker login ghcr.io -u USER --password-stdin    # ⭐ scriptable, no shell history
docker logout ghcr.io

docker tag myapp:v1 ghcr.io/myorg/myapp:v1
docker push ghcr.io/myorg/myapp:v1
docker pull ghcr.io/myorg/myapp:v1

# AWS ECR
aws ecr get-login-password --region us-east-1 \
  | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Local registry for testing
docker run -d -p 5000:5000 --name registry registry:2
docker tag myapp:v1 localhost:5000/myapp:v1 && docker push localhost:5000/myapp:v1

# Inspect a remote image WITHOUT pulling it
docker manifest inspect ghcr.io/myorg/myapp:v1
crane digest ghcr.io/myorg/myapp:v1            # from google/go-containerregistry
skopeo inspect docker://ghcr.io/myorg/myapp:v1
```

**Tagging strategy:**

```bash
docker build \
  -t "ghcr.io/org/app:${GIT_SHA}" \        # ⭐ immutable — this is what you deploy
  -t "ghcr.io/org/app:v1.4.2" \            # semantic version
  -t "ghcr.io/org/app:latest" \            # convenience only — never deploy this
  .
```

---

## Cleanup & Disk

```bash
docker system df                       # ⭐ start here: images / containers / volumes / cache
docker system df -v                    # per-item breakdown

docker container prune                 # remove stopped containers
docker image prune                     # dangling (untagged) images
docker image prune -a --filter "until=168h"    # unused images older than a week
docker volume prune                    # ⚠️ unused volumes — this is data
docker network prune
docker builder prune --filter "until=48h"

docker system prune                    # containers + networks + dangling images + cache
docker system prune -a                 # ⚠️ + every image not used by a running container
docker system prune -a --volumes       # ⚠️⚠️ + all unused volumes. Read twice.

# Cap log growth (the usual cause of a full /var/lib/docker)
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": { "max-size": "10m", "max-file": "3" }
}
# then: sudo systemctl restart docker
```

---

## Security

```bash
trivy image myapp:v1                                  # ⭐ CVE scan
trivy image --severity HIGH,CRITICAL --exit-code 1 myapp:v1     # gate CI on it
trivy image --ignore-unfixed myapp:v1                 # only actionable findings
trivy fs .                                            # scan the source tree
grype myapp:v1
docker scout cves myapp:v1
syft myapp:v1 -o spdx-json > sbom.json                # generate an SBOM
hadolint Dockerfile                                   # lint the Dockerfile
dockle myapp:v1                                       # image best-practice audit
```

**Checklist:**

- [ ] Non-root `USER` in the final stage
- [ ] Minimal base image (`-slim`, `alpine`, `distroless`, or `scratch`)
- [ ] Multi-stage build — no compilers or dev dependencies shipped
- [ ] Pinned base image tag, ideally by digest
- [ ] No secrets in `ENV`, `ARG`, or any layer — use BuildKit `--secret` or runtime injection
- [ ] `.dockerignore` excludes `.git`, `.env`, keys
- [ ] `--read-only` root filesystem with an explicit `tmpfs` where writes are needed
- [ ] `--cap-drop ALL`, adding back only what's required
- [ ] `--security-opt no-new-privileges:true`
- [ ] Memory and CPU limits set
- [ ] Image scanned in CI and the build **fails** on HIGH/CRITICAL
- [ ] Never mount `/var/run/docker.sock` into a container you don't fully trust — it is root on the host

---

## Error Decoder

| Message / symptom | Cause | Fix |
|-------------------|-------|-----|
| `permission denied ... /var/run/docker.sock` | Your user isn't in the `docker` group | `sudo usermod -aG docker $USER`, then log out and back in |
| `bind: address already in use` | Host port is taken | `ss -tlnp \| grep :8080`, pick another port |
| Container exits immediately, code **0** | Main process isn't long-running / forked to background | Run in the foreground (`nginx -g 'daemon off;'`) |
| Exit code **125** | Docker itself rejected the run | Bad `docker run` flags |
| Exit code **126** | Entrypoint found but not executable | `chmod +x`, check for CRLF line endings |
| Exit code **127** | Command not found | Wrong path, or missing from a slim base image |
| Exit code **137** | SIGKILL — usually **OOM** | `docker inspect -f '{{.State.OOMKilled}}'`; raise `--memory` |
| Exit code **143** | SIGTERM — normal `docker stop` | Not an error |
| `no such host` between containers | Not on the same user-defined network | `docker network create` + `--network`; use the container name |
| `connection refused` to your own app | App bound to `127.0.0.1` inside the container | Bind to `0.0.0.0` |
| `no space left on device` | Docker disk usage | `docker system df` then prune; cap log size |
| `manifest unknown` / `pull access denied` | Wrong tag, or private image | Check the tag; `docker login` |
| `toomanyrequests` | Docker Hub anonymous rate limit | Authenticate, or mirror the image |
| `exec format error` | Architecture mismatch (arm64 image on amd64) | `--platform linux/amd64`, or build multi-arch |
| Build is slow every time | Layer cache invalidated too early | Copy dependency manifests before source code |
| Changes not appearing | You rebuilt but reran the old image | `docker compose up -d --build`; check the tag |

---

<div align="center">

[← Module 05 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
