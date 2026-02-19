## Infrastructure & DevOps Audit Report

### Executive Summary

The PACO multi-agent system spans two docker-compose topologies (19 services in gobierno-queretaro, 8 services in paco) with significant security gaps that must be addressed before production hardening. Critical issues include a Docker socket mount granting root-equivalent host access, hardcoded database credentials, exposed infrastructure ports without authentication, absence of resource limits across all 27+ containers, and no CI/CD pipeline. The infrastructure template pattern for gobierno-queretaro agents is well-designed for consistency but lacks security hardening across the board.

### Critical Findings

**CRIT-001: Docker Socket Mount on paco-backend Grants Root-Equivalent Host Access**
- File: `paco/docker-compose.yml:120`
- Issue: The `paco-backend` service mounts `/var/run/docker.sock:/var/run/docker.sock:ro`. Even with `:ro`, any process inside this container can issue Docker API commands (create containers, exec into other containers, mount host filesystem volumes) granting effective root access to the host machine.
- Impact: If the paco-backend API is compromised (e.g., via an API vulnerability, dependency exploit, or credential leak), the attacker gains full control over the host system and every other container. This is the single most dangerous configuration in the entire system.
- Recommendation: Remove the Docker socket mount entirely. If container orchestration is required, use a restricted Docker API proxy such as Tecnativa/docker-socket-proxy that allowlists only specific API endpoints (e.g., only `GET /containers/json`). Alternatively, move infrastructure management to a separate privileged sidecar with strict network isolation.

**CRIT-002: Hardcoded Postgres Credentials in gobierno-queretaro**
- File: `gobierno-queretaro/docker-compose.yml:31` (and repeated on lines 81, 109, 137, 164, 191, 218, 245, 271, 299, 326, 353, 380, 407, 496-497)
- Issue: Database credentials are hardcoded as `postgres:postgres` in every service's `DATABASE_URL` environment variable and in the Postgres container's `POSTGRES_USER`/`POSTGRES_PASSWORD`. These are not sourced from environment variables or secrets management.
- Impact: Anyone with access to the docker-compose file, container inspection, or repository history has full database access. Credentials cannot be rotated without modifying and redeploying all 15 services simultaneously. The superuser account `postgres` is used for application connections.
- Recommendation: Use `${POSTGRES_PASSWORD}` variable references sourced from `.env` or Docker secrets. Create a dedicated application user with limited privileges (not superuser). Use separate credentials per agent if feasible.

**CRIT-003: Insecure Default Secrets in paco with Placeholder Values**
- File: `paco/docker-compose.yml:84-86`
- Issue: Langfuse configuration uses dangerous defaults: `NEXTAUTH_SECRET` defaults to `your-nextauth-secret-change-me`, `SALT` defaults to `your-salt-change-me`, and `ENCRYPTION_KEY` defaults to 64 zero characters (`0000...0`). The `paco-backend` has `SECRET_KEY` defaulting to `your-secret-key-change-me` (line 109). These defaults are active when the `.env` file is not configured.
- Impact: If deployed without changing defaults, session tokens are predictable, encryption is effectively null (all-zeros key), and API authentication can be bypassed. An attacker who knows these defaults (which are committed to source control) can forge sessions and decrypt stored data.
- Recommendation: Remove default values for all secret environment variables (use `${VAR}` without `:-default`). Fail fast on startup if secrets are not provided. Generate strong random values during deployment.

**CRIT-004: ClickHouse Credentials Hardcoded in docker-compose**
- File: `paco/docker-compose.yml:10-11, 81-82`
- Issue: ClickHouse credentials are hardcoded directly in the docker-compose file: `CLICKHOUSE_USER: langfuse`, `CLICKHOUSE_PASSWORD: langfuse_secret`. The Langfuse service also references these hardcoded values on lines 80-82. These are not parameterized through environment variables.
- Impact: Credentials are visible in version control history and cannot be rotated without modifying the compose file. Combined with exposed ClickHouse ports (CRIT-005), this allows unauthenticated external access.
- Recommendation: Move all ClickHouse credentials to environment variables sourced from `.env` or a secrets manager.

**CRIT-005: Infrastructure Ports Exposed to Host Network (paco)**
- File: `paco/docker-compose.yml:17-18, 39-40, 57-58`
- Issue: Critical infrastructure services expose ports directly to the host (and potentially to the network):
  - ClickHouse: ports `8123:8123` (HTTP) and `9000:9000` (native protocol)
  - PostgreSQL: port `5432:5432`
  - Redis: port `6379:6379`
  None of these services have authentication enabled by default (Redis has no password; Postgres uses weak defaults).
- Impact: Any host on the network can connect to these databases directly, read/write data, or execute arbitrary commands. Redis without authentication allows `CONFIG SET` to write arbitrary files. Postgres with weak credentials allows full database access.
- Recommendation: Remove port mappings for infrastructure services (they only need internal Docker network access). If host access is needed for development, bind to `127.0.0.1` only (e.g., `127.0.0.1:5432:5432`). Enable Redis `requirepass`. Use strong Postgres credentials.

### High Priority Findings

**HIGH-001: No Resource Limits on Any Container**
- File: `gobierno-queretaro/docker-compose.yml` (entire file), `paco/docker-compose.yml` (entire file)
- Issue: None of the 27+ services across both compose files define `deploy.resources.limits` for CPU or memory. The gobierno-queretaro system runs 13 LLM-calling agents plus orchestrator, each capable of unbounded memory growth.
- Impact: A single agent experiencing a memory leak or processing a large response can consume all host memory, causing OOM kills across all containers and bringing down the entire system. In a government production system serving citizens, this creates availability risk.
- Recommendation: Add memory and CPU limits to all services. Suggested starting points: agents `mem_limit: 512m`, orchestrator `mem_limit: 1g`, Redis `mem_limit: 256m`, Postgres `mem_limit: 1g`. Monitor and adjust based on actual usage patterns.

**HIGH-002: No Network Segmentation - Flat Single Bridge Network**
- File: `gobierno-queretaro/docker-compose.yml:554-556`, `paco/docker-compose.yml:182-184`
- Issue: Both systems use a single flat bridge network (`gobierno-network` and `paco-network` respectively). Every container can communicate with every other container on all ports without restriction.
- Impact: If any agent container is compromised, it has direct network access to Postgres, Redis, all other agents, and the orchestrator. In gobierno-queretaro, all 13 agent containers can directly access the database and each other, when they should only need to communicate with the orchestrator.
- Recommendation: Implement network segmentation with at least three networks: (1) `frontend-net` for external-facing services, (2) `backend-net` for agents and orchestrator, (3) `data-net` for databases. Agents should only be on `backend-net`; only the orchestrator should bridge between `frontend-net` and `backend-net`; only services needing database access should be on `data-net`.

**HIGH-003: Jaeger Ports Exposed Externally Without Authentication**
- File: `gobierno-queretaro/docker-compose.yml:459-461`
- Issue: Jaeger exposes three ports to the host: `16686` (UI), `4317` (OTLP gRPC), and `4318` (OTLP HTTP). The Jaeger all-in-one image has no built-in authentication.
- Impact: Anyone with network access can view all distributed traces (which may contain sensitive citizen query data, API keys in headers, PII), and inject arbitrary trace data via the OTLP endpoints. The OTLP endpoints (`4317`, `4318`) should never be exposed externally as they accept arbitrary data ingestion.
- Recommendation: Remove port mappings for `4317` and `4318` (they only need internal Docker network access). Bind `16686` to `127.0.0.1` only, or put Jaeger UI behind an authenticated reverse proxy.

**HIGH-004: All Agent Ports Individually Exposed to Host**
- File: `gobierno-queretaro/docker-compose.yml:76, 103, 130, 157, 185, 211, 238, 265, 292, 319, 346, 373, 400`
- Issue: Each of the 13 agent services exposes its port individually to the host (9101-9113). These agents should only be accessible through the orchestrator, which is the designed routing layer.
- Impact: The port exposure bypasses the orchestrator's rate limiting, authentication, and routing logic. External clients can call agent APIs directly, circumventing all access controls. This creates 13 additional attack surface endpoints.
- Recommendation: Remove all agent port mappings. Agents should only communicate via the internal Docker network through the orchestrator. Keep only the orchestrator port (9100) exposed for external access.

**HIGH-005: All Containers Run as Root (gobierno-queretaro)**
- File: All Dockerfiles in `gobierno-queretaro/agents/*/Dockerfile`, `gobierno-queretaro/orchestrator/Dockerfile`, `gobierno-queretaro/voice-gateway/Dockerfile`
- Issue: None of the 16 gobierno-queretaro Dockerfiles create or switch to a non-root user. All application processes run as `root` inside their containers.
- Impact: If any container is compromised, the attacker has root privileges within the container, making container escape exploits more impactful. Combined with the lack of network segmentation (HIGH-002), a root compromise in any agent gives broader attack capability.
- Recommendation: Add `RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app` and `USER appuser` to all Dockerfiles. The paco-backend Dockerfile (line 23-24) already demonstrates this pattern correctly.

**HIGH-006: Unpinned `latest` Tag for Jaeger Image**
- File: `gobierno-queretaro/docker-compose.yml:455`
- Issue: The Jaeger service uses `image: jaegertracing/all-in-one:latest`. The `latest` tag is mutable and can change without notice.
- Impact: A `docker-compose pull` or fresh deployment could introduce a breaking version change, or in a supply-chain attack scenario, a compromised image. Builds are not reproducible.
- Recommendation: Pin to a specific version (e.g., `jaegertracing/all-in-one:1.62`). Similarly, `langfuse/langfuse:latest` in `paco/docker-compose.yml:69` should be pinned.

**HIGH-007: Unpinned `latest` Tag for Langfuse Image**
- File: `paco/docker-compose.yml:69`
- Issue: The Langfuse service uses `image: langfuse/langfuse:latest`, same problem as HIGH-006.
- Impact: Non-reproducible deployments, potential breaking changes, supply chain risk.
- Recommendation: Pin to a specific Langfuse version tag.

**HIGH-008: CEA SOAP Credentials in .env.example**
- File: `gobierno-queretaro/.env.example:14-15`
- Issue: The `.env.example` file contains what appear to be real default credentials: `CEA_SOAP_USERNAME=WSGESTIONDEUDA` and `CEA_SOAP_PASSWORD=WSGESTIONDEUDA`. These look like actual service account credentials for the CEA (water utility) SOAP API, not placeholders.
- Impact: If these are real credentials (same username and password suggests a default/test account), they are committed to version control and visible to anyone with repository access.
- Recommendation: Replace with placeholder values (e.g., `your-cea-username`). Verify whether these are real production credentials and rotate immediately if so.

### Medium Priority Findings

**MED-001: Inconsistent Python Versions Across Systems**
- File: `gobierno-queretaro/orchestrator/Dockerfile:6` (Python 3.12-slim), `gobierno-queretaro/voice-gateway/Dockerfile:1` (Python 3.11-slim), `paco/backend/Dockerfile:1` (Python 3.11-slim)
- Issue: The gobierno-queretaro agents and orchestrator use Python 3.12-slim, while the voice gateway and paco-backend use Python 3.11-slim. This creates potential compatibility issues with shared dependencies.
- Impact: Dependency resolution differences between Python 3.11 and 3.12 (e.g., `asyncio` changes, typing features) can cause subtle runtime bugs that only appear in specific services.
- Recommendation: Standardize on a single Python version (3.12-slim is the most current used). Update voice-gateway and paco-backend to match.

**MED-002: Inconsistent Postgres Versions Between Systems**
- File: `gobierno-queretaro/docker-compose.yml:491` (postgres:15-alpine), `paco/docker-compose.yml:29` (postgres:16-alpine)
- Issue: The two systems use different PostgreSQL major versions (15 vs 16). If data needs to be migrated between systems or if they share operational procedures, version differences can cause issues.
- Impact: SQL feature differences, extension compatibility, and pg_dump format differences between Postgres 15 and 16. Operational runbooks must account for version-specific behavior.
- Recommendation: Align on a single Postgres version (16-alpine as the newer version). Pin to a specific minor version for reproducibility (e.g., `postgres:16.6-alpine`).

**MED-003: Deploy Script Port Mapping Mismatch**
- File: `gobierno-queretaro/scripts/deploy.sh:156-169`
- Issue: The deploy script health checks use ports 8000-8013 (lines 156-169), but the docker-compose.yml maps agents to ports 9100-9113. The script will always report services as "starting..." because it checks the wrong ports.
- Impact: The deployment script gives false negative health status - operators cannot verify deployment success via the script. This undermines deployment confidence and could hide failures.
- Recommendation: Update the deploy script port numbers to match docker-compose.yml mappings (9100-9113), or use `docker-compose exec` to check health internally.

**MED-004: No .dockerignore for gobierno-queretaro Services**
- File: `gobierno-queretaro/` (directory-level)
- Issue: The gobierno-queretaro directory has no `.dockerignore` file. The build context is the entire `gobierno-queretaro/` directory (context: `.` in docker-compose.yml). Only `paco/backend/` and `paco/frontend/` have `.dockerignore` files.
- Impact: Docker build contexts include unnecessary files (`.git`, `__pycache__`, `tests/`, `research/`, `training/`, `scripts/`, all agent directories for every agent build). This slows builds significantly and increases image size. Sensitive files could be accidentally included in images.
- Recommendation: Add a `.dockerignore` file at the gobierno-queretaro root that excludes `.git`, `__pycache__`, `*.pyc`, `tests/`, `research/`, `scripts/`, `.env`, and any other non-essential directories.

**MED-005: No Multi-Stage Builds for gobierno-queretaro Python Services**
- File: All Dockerfiles in `gobierno-queretaro/agents/*/Dockerfile`, `gobierno-queretaro/orchestrator/Dockerfile`
- Issue: All 15 gobierno-queretaro Dockerfiles use single-stage builds. Build tools (pip, apt caches for curl) remain in the final image. Contrast with `paco/frontend/Dockerfile` which correctly uses a 3-stage build (base, deps, builder, runner) and `paco/mcp-servers/cea-tools/Dockerfile` which uses a 2-stage build.
- Impact: Final images are larger than necessary, containing build artifacts and development tools. With 15 near-identical agent images, this multiplied inefficiency wastes significant disk space and increases attack surface.
- Recommendation: Consider multi-stage builds for the Python services, or at minimum ensure build-only dependencies are cleaned up. The `--no-install-recommends` flag is already used which is good.

**MED-006: MCP Server Dockerfiles Missing Security Hardening**
- File: `paco/mcp-servers/agora-tools/Dockerfile`, `paco/mcp-servers/cea-tools/Dockerfile` (agora-tools only)
- Issue: The `agora-tools` Dockerfile (14 lines) has no health check, no non-root user, and no multi-stage build. It uses `npm install` instead of `npm ci`. The `cea-tools` Dockerfile is well-structured with multi-stage build, non-root user, and health check - showing inconsistency.
- Impact: The agora-tools container runs as root with no way to determine its health status. Inconsistent patterns make the system harder to maintain and audit.
- Recommendation: Apply the cea-tools Dockerfile pattern (multi-stage, non-root user, health check) to agora-tools as well.

**MED-007: Unpinned Python Dependencies with Floor Versions Only**
- File: `gobierno-queretaro/agents/_template/requirements.txt`, `gobierno-queretaro/orchestrator/requirements.txt`
- Issue: All Python dependencies use floor version specifiers (e.g., `langgraph>=0.2.0`, `fastapi>=0.115.0`). There are no upper bounds or pinned versions. No `requirements.lock` or `pip freeze` output is used.
- Impact: Every `docker build` can install different dependency versions, making builds non-reproducible. A breaking change in any dependency (LangGraph, LangChain, Anthropic SDK) will break all 15 services simultaneously with no rollback path.
- Recommendation: Generate a `requirements.lock` file with pinned versions using `pip-compile` (pip-tools) or use Poetry/PDM with lock files. Pin at least major+minor versions (e.g., `langgraph>=0.2.0,<0.3.0`).

**MED-008: Redis Without Authentication**
- File: `gobierno-queretaro/docker-compose.yml:474-488`, `paco/docker-compose.yml:49-65`
- Issue: Both Redis instances run without authentication. The gobierno-queretaro Redis is not port-exposed (good), but the paco Redis exposes port 6379 to host (CRIT-005). Neither uses `requirepass`.
- Impact: In paco, anyone with network access can read/write to Redis, potentially poisoning session caches, injecting messages via pub/sub, or extracting cached citizen data. Even in gobierno-queretaro, any compromised container on the bridge network can access Redis without authentication.
- Recommendation: Add `--requirepass ${REDIS_PASSWORD}` to the Redis command in both systems. Update all service connection strings to include the password.

**MED-009: Healthcheck Port Mismatch in maria-claude/Dockerfile**
- File: `Dockerfile:19-20` (root), `maria-claude/Dockerfile:19-20`
- Issue: Both the root Dockerfile and maria-claude Dockerfile expose port 3000 (`EXPOSE 3000`) but run health checks against port 3002 (`wget ... http://localhost:3002/health`). The HEALTHCHECK will always fail because it is checking the wrong port.
- Impact: Docker will perpetually report this container as unhealthy, and any `depends_on` with `condition: service_healthy` will never be satisfied. Restart policies may continuously restart healthy containers.
- Recommendation: Align the health check port with the actual application port (either change EXPOSE to 3002 or change the health check to port 3000).

### Low Priority / Improvements

**LOW-001: No Container Logging Strategy**
- File: `gobierno-queretaro/docker-compose.yml`, `paco/docker-compose.yml`
- Issue: No logging driver configuration is specified for any service. Docker defaults to the `json-file` driver with no size limits, meaning container logs will grow unbounded on disk.
- Impact: Over time (days/weeks in production), log files can fill up the host disk, causing system-wide failures. With 19 services in gobierno-queretaro, this is accelerated.
- Recommendation: Configure a logging driver with rotation for all services: `logging: { driver: "json-file", options: { max-size: "10m", max-file: "3" } }`. For production, consider shipping logs to a centralized system (ELK, Loki, CloudWatch).

**LOW-002: No Backup/Recovery Strategy for Volumes**
- File: `gobierno-queretaro/docker-compose.yml:558-560`, `paco/docker-compose.yml:176-180`
- Issue: Both systems use Docker named volumes for persistent data (postgres_data, redis_data, clickhouse_data, clickhouse_logs) but there is no backup configuration, cron job, or documented recovery procedure.
- Impact: A host failure, accidental `docker volume rm`, or volume corruption would result in complete data loss (citizen interaction history, agent memories, analytics data, tickets).
- Recommendation: Implement automated Postgres backups using `pg_dump` on a schedule (e.g., daily via cron container or host cron). Store backups off-host (S3, GCS). Document recovery procedures. Consider using Postgres replication for high availability.

**LOW-003: No CI/CD Pipeline**
- File: N/A (no `.github/workflows/`, `.gitlab-ci.yml`, or `Jenkinsfile` found)
- Issue: The repository has no CI/CD pipeline. The only deployment mechanism is the manual `gobierno-queretaro/scripts/deploy.sh` script.
- Impact: No automated testing, linting, security scanning, or image vulnerability scanning before deployment. Manual deployments are error-prone and not auditable. No staging/production environment separation is enforced.
- Recommendation: Implement a CI/CD pipeline (GitHub Actions, GitLab CI) with stages for: lint/format check, unit tests, Docker image build, image vulnerability scanning (Trivy/Snyk), staging deployment, production deployment with approval gate.

**LOW-004: No Health Check Dependency Conditions in gobierno-queretaro**
- File: `gobierno-queretaro/docker-compose.yml:54-56, 85-87` (and all agent `depends_on` blocks)
- Issue: Agent services use `depends_on: [redis, postgres]` without `condition: service_healthy`. This means agents start immediately after containers are created, not after they are healthy. Compare with paco which correctly uses `condition: service_healthy` (lines 73-76, 101-105).
- Impact: During cold starts, agents may fail to connect to Postgres/Redis because those services are still initializing. The `restart: unless-stopped` policy will eventually recover, but initial startup will have errors and unnecessary restarts.
- Recommendation: Change all `depends_on` entries to use `condition: service_healthy`, matching the paco pattern.

**LOW-005: `npm install` vs `npm ci` Inconsistency**
- File: `paco/mcp-servers/agora-tools/Dockerfile:8`, `Dockerfile:8` (root), `maria-claude/Dockerfile:8`
- Issue: Some Dockerfiles use `npm install` (agora-tools, root Dockerfile, maria-claude) while others correctly use `npm ci` (paco frontend, paco cea-tools). `npm install` can modify `package-lock.json` and install different versions.
- Impact: Non-reproducible builds; the installed dependencies may differ from what was tested locally.
- Recommendation: Use `npm ci` in all Dockerfiles for deterministic installs.

**LOW-006: Development Dependencies Installed in Production Image (paco-backend)**
- File: `paco/backend/requirements.txt:57-62`
- Issue: The paco-backend requirements.txt includes development dependencies (`pytest`, `pytest-asyncio`, `black`, `ruff`) that are installed in the production Docker image since there is no separation between dev and prod dependencies.
- Impact: Increases image size and attack surface. Testing/formatting tools are present in production containers.
- Recommendation: Split into `requirements.txt` (production) and `requirements-dev.txt` (development), or use a tool like Poetry with dependency groups.

**LOW-007: Node.js Version Inconsistency Across Dockerfiles**
- File: `paco/frontend/Dockerfile:1` (node:20-alpine), `paco/mcp-servers/cea-tools/Dockerfile:6` (node:20-alpine), `paco/mcp-servers/agora-tools/Dockerfile:1` (node:20-alpine), `Dockerfile:1` (node:22-alpine), `maria-claude/Dockerfile:1` (node:22-alpine)
- Issue: PACO services use Node.js 20 while maria-claude and root Dockerfile use Node.js 22. Node 20 is LTS (supported), Node 22 is current.
- Impact: Minor - both versions are supported, but inconsistency adds maintenance burden.
- Recommendation: Standardize on Node.js 20 LTS across all services for stability, or upgrade all to 22 when it becomes LTS.

**LOW-008: Deploy Script Sources .env Without Sanitization**
- File: `gobierno-queretaro/scripts/deploy.sh:95`
- Issue: The deploy script runs `source .env` which directly executes the `.env` file as a shell script. If the `.env` file contains shell metacharacters or commands, they will be executed.
- Impact: Low risk in practice since the `.env` file is developer-controlled, but a maliciously crafted `.env` could execute arbitrary commands during deployment.
- Recommendation: Use `set -a; source .env; set +a` or parse the `.env` file with `export $(grep -v '^#' .env | xargs)` for safer variable loading.

### Positive Observations

1. **Consistent agent template pattern**: The gobierno-queretaro system uses a well-designed template pattern (`agents/_template/`) that ensures all 13 agents have consistent Dockerfile structure, dependencies, and configuration. This is excellent for maintainability.

2. **Good health check coverage**: Almost every service has health checks defined, both in Dockerfiles (HEALTHCHECK instruction) and in docker-compose.yml. Redis uses `redis-cli ping` (appropriate), Postgres uses `pg_isready` (appropriate), and ClickHouse uses `wget` against its ping endpoint.

3. **Internal-only networking for gobierno-queretaro databases**: Redis and Postgres in gobierno-queretaro deliberately do not expose ports to the host (commented notes on lines 478 and 498-499), showing security awareness. This is correctly more secure than the paco configuration.

4. **paco-backend runs as non-root**: The `paco/backend/Dockerfile` (lines 23-24) creates and switches to a non-root user, demonstrating the correct security pattern. The `paco/frontend/Dockerfile` also runs as a non-root user (nextjs:nodejs).

5. **paco-frontend uses multi-stage builds**: The `paco/frontend/Dockerfile` uses a proper 3-stage build (deps, builder, runner) with standalone output, following Next.js best practices. The `paco/mcp-servers/cea-tools/Dockerfile` also uses multi-stage builds with production dependency separation.

6. **Appropriate restart policies**: All services use `restart: unless-stopped`, which is appropriate for a production system (survives host reboot, but allows intentional stops).

7. **Good dependency caching in Dockerfiles**: Requirements/package files are copied and installed before application code in all Dockerfiles, properly leveraging Docker layer caching to speed up rebuilds.

8. **paco uses healthcheck conditions for startup ordering**: The paco docker-compose file uses `condition: service_healthy` on `depends_on` blocks (lines 73-76, 101-105), ensuring proper startup sequencing.

### Metrics

- Files reviewed: 32
- Critical findings: 5
- High findings: 8
- Medium findings: 9
- Low findings: 8
