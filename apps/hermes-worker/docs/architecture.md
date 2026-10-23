# Hermes Worker — Architecture & Design Rationale

---

## 1. Cloud Infrastructure & Ephemeral Execution Model

`hermes-worker` runs as an autonomous, run-and-die batch CLI in AWS. Rather than maintaining a long-running daemon with in-process schedulers (e.g. Celery Beat or APScheduler), execution is orchestrated entirely through external cloud scheduling.

### Architecture Topology

```text
┌─────────────────────────────────────────────────────────────────────┐
│                     TRIGGER (3x per day)                            │
│                                                                     │
│            ┌──────────────────────────────────┐                     │
│            │    EventBridge Scheduler         │                     │
│            │    (cron — 3 times/day)          │                     │
│            └────────────────┬─────────────────┘                     │
└─────────────────────────────┼───────────────────────────────────────┘
                              │ triggers ECS RunTask
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     COMPUTE (AWS Fargate)                           │
│                                                                     │
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │  hermes-cluster (ECS)                                        │  │
│   │                                                              │  │
│   │   ┌──────────────────────────────────────────────────────┐   │  │
│   │   │  hermes-worker Task (Fargate)                        │   │  │
│   │   │  0.25 vCPU  •  512 MB RAM  •  x86 Linux              │   │  │
│   │   │                                                      │   │  │
│   │   │   ┌────────────────────────────────────────────┐     │   │  │
│   │   │   │  hermes-worker Container                   │     │   │  │
│   │   │   │  Image: ECR hermes-worker:latest           │     │   │  │
│   │   │   │  Python CLI (hermes-worker run-all)        │     │   │  │
│   │   │   │  HTTP calls + DB calls (5–10 min)          │     │   │  │
│   │   │   │  Process exits -> container destroyed      │     │   │  │
│   │   │   └────────────────────────────────────────────┘     │   │  │
│   │   └──────────────────────────────────────────────────────┘   │  │
│   └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
          │ logs streamed                        │ image pulled
          ▼                                      ▲
┌──────────────────────┐            ┌────────────────────────┐
│  CloudWatch Logs     │            │  ECR Repository        │
│  /ecs/hermes-worker  │            │  hermes-worker:latest  │
│  (never expires)     │            │  ~319 MB stored        │
└──────────────────────┘            └────────────────────────┘
```

### Step-by-Step Lifecycle of a Single Run

1. **EventBridge Scheduler fires**: At the scheduled time (3 times per day), EventBridge sends a `RunTask` API call to the ECS cluster `hermes-cluster`.
2. **ECS instructs Fargate**: AWS Fargate dynamically allocates 0.25 vCPU and 512 MB of RAM from the shared compute pool on demand. No server is pre-running or idle between intervals.
3. **ECR image is pulled**: Fargate pulls the `hermes-worker:latest` container image from the private Amazon ECR repository.
4. **Python worker runs**: The container initializes, establishes its database connection pool inside `db_lifespan()`, and executes its tasks (`hermes-worker run-all`: lifecycle transitions followed by due RSS feed synchronization). Total runtime is typically 5 to 10 minutes.
5. **Worker exits cleanly**: Once the batch process terminates, ECS flags the task as `STOPPED` and Fargate immediately deallocates the compute resources. Billing stops at container termination.
6. **Log persistence**: All output (`stdout`/`stderr`) is streamed in real time to Amazon CloudWatch Logs under `/ecs/hermes-worker` for auditing and historical telemetry.

### Why Ephemeral Compute?

- **Memory Leak Protection**: Untrusted third-party RSS XML parsing, feed scraping, and DOM manipulation in Python can accumulate uncollected memory across long-lived processes. Terminating the process on completion guarantees complete memory reclamation by the operating system.
- **Clean Connection Lifecycles**: Encapsulating commands in `db_lifespan()` ensures the SQLAlchemy `AsyncEngine` pool initializes on process startup and cleanly calls `engine.dispose()` on process teardown.
- **External Scheduling**: Cloud schedulers natively manage execution intervals, execution timeouts, retries, and dead-letter alarms, eliminating in-process concurrency bugs across worker restarts.
- **Deployment Reference**: Production container builds and registry publication are managed in `.github/workflows/cd-worker.yml` and `apps/hermes-worker/Dockerfile`.

---

## 2. Ingestion Pipeline & Cost Optimization

The ingestion stages in `services/sync.py` are structured to minimize token consumption and inference latency:

### A. Embed Before Extract (Vector Pre-Filtering)

Computing dense vector embeddings and querying candidate events via PostGIS `pgvector` HNSW cosine distance search (`EventService.get_active_events_by_embeddings`) runs prior to LLM extraction:

- Rather than passing articles to an LLM for pairwise textual comparison (which scales quadratically with incoming articles), PostGIS identifies existing candidate events within the cosine distance threshold.
- The LLM prompt receives only the candidate event IDs or evaluates whether the article represents a novel incident.
- _Status_: Believed, not measured — based on algorithmic complexity and token estimation rather than comparative production benchmarks.

### B. Bounded Batch Sizing & Concurrency

Articles within a feed are processed in bounded chunks defined by `ARTICLE_BATCH_SIZE` (in `libs/shared/hermes-ai/src/hermes_ai/core/constants.py`):

- Because the Fargate task is allocated only 512 MB of RAM, feeds and extracted articles must never be accumulated globally in memory. Processing feeds through bounded batches with an `asyncio.Semaphore` enforces strict memory constraints.
- _Status_: Believed, not measured — single-article prompts multiply network round-trips, whereas large batches are suspected to increase index-mapping errors in small parameter models.

### C. Source Credibility & Consensus Scoring

When an incoming article corroborates an existing incident, the event's `article_count` increments and its score increases using the weight defined in `CREDIBILITY_WEIGHTS` (in `libs/shared/hermes-db/src/hermes_db/services/ranking.py`). If the event was previously in `STALE` status, it is automatically reactivated to `ACTIVE`.

---

## 3. Lifecycle Decay & Status Transitions

- **Exponential Score Decay**: Event trending scores diminish over time based on `HOURLY_DECAY_FACTOR` (in `libs/shared/hermes-db/src/hermes_db/services/ranking.py`), allowing breaking stories to dominate the viewport while older stories fade.
- **State Progression**: Inactive events transition from `ACTIVE` to `STALE` past `EVENT_STALE_HRS`, and from `STALE` to `ARCHIVED` past `EVENT_ARCHIVE_HRS` (both defined in `libs/shared/hermes-db/src/hermes_db/core/config.py`).
- **Resource Teardown**: The CLI disposes of all database connections on exit, returning a non-zero exit code (`sys.exit(1)`) if an unhandled error occurs during lifecycle or sync tasks.
