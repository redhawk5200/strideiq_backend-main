# StrideIQ Backend

FastAPI backend for the StrideIQ mobile application. The service ingests health telemetry, manages onboarding flows, and generates AI-driven coaching insights built on top of user biometrics stored in PostgreSQL.

## High-Level Architecture

- **FastAPI** application (`app/main.py`) with async lifespan start-up that guarantees database schemas are in place.
- **PostgreSQL** for persistence, accessed through SQLAlchemy 2.x async session factories.
- **Clerk** for authentication – validated per request via `ClerkAuthMiddleware`.
- **OpenAI** integrations in the recommendation and VO₂ services for generating natural-language feedback.
- **AWS S3 (optional)** for document storage hooks (legacy functionality is mostly removed, but credentials remain for future use).

## Repository Layout

```
app/
├── api/v1/                   # Versioned API routers and controllers
├── core/                     # Configuration, logging, shared utilities
├── database/                 # SQLAlchemy engine/session setup
├── middlewares/              # Authentication and usage tracking middleware
├── models/                   # Declarative SQLAlchemy models
├── schemas/                  # Pydantic request/response models
├── services/                 # Domain services (onboarding, health sync, AI insights)
├── utils/                    # Currently minimal; legacy RAG utilities removed
alembic/                      # Database migrations
docker-compose.yml            # Local container tooling (app container only)
requirements.txt              # Runtime dependencies
frozen-requirements.txt       # Pinned lock snapshot
```

## Prerequisites

- Python 3.12+
- PostgreSQL instance reachable from the application
- Optional: Access to OpenAI API (for AI insights) and AWS credentials (if you re-enable document storage)

## Environment Variables

Create a `.env` file in the project root with at least the following keys:

| Variable | Description |
| --- | --- |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | PostgreSQL connection parameters |
| `DB_SSLMODE` | Optional, defaults to enforced SSL |
| `OPENAI_API_KEY` | Required for recommendations and VO₂ insight services |
| `CLERK_SECRET_KEY`, `CLERK_WEBHOOK_SECRET` | Backend Clerk integration |
| `AWS_ACCESS_KEY`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`, `AWS_S3_BUCKET_NAME` | Only needed for legacy upload code or future S3 usage |

All configuration is loaded in `app/core/config.py`.

## Local Development

### 1. Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Database

Create the target database and ensure connectivity from your machine. To apply migrations:

```bash
alembic upgrade head
```

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

OpenAPI/Swagger docs are served at `http://127.0.0.1:8000/docs`.

### 4. Docker Workflow (Optional)

`docker-compose.yml` builds only the backend container. You still need an accessible PostgreSQL instance.

```bash
docker compose up --build
```

## Core Modules

- **Onboarding Service** (`app/services/onboarding_service.py`): handles user profile creation, goals, training preferences, medical conditions, and progress tracking.
- **Health Sync Service** (`app/services/health_sync_service.py`): ingests batched health metrics (heart rate, steps, VO₂, workouts) with deduplication safeguards.
- **Coaching Recommendations Service** (`app/services/coaching_recommendations_service.py`): aggregates recent health data, builds prompts, and calls OpenAI for generated guidance and quick actions.
- **VO₂ Services** (`app/services/vo2_analysis_service.py`, `app/services/vo2_insights_service.py`): calculates statistical trends and produces narrative summaries via OpenAI.
- **Middleware**:
  - `ClerkAuthMiddleware` guards non-whitelisted routes.
  - `usage_tracking_middleware.py` estimates prompt token usage for future analytics.

## Database Notes

- SQLAlchemy declarative models live under `app/models`. IDs use cuid for compact string identifiers.
- Relationship-heavy entities (e.g., `UserProfile`, `UserGoal`, `TrainingPreferences`) track cascading deletes to keep data consistent.
- `app/database/connection.py` configures an async engine with connection pooling defaults suitable for production but still friendly in dev.
- Migrations are tracked with Alembic; see `alembic/versions` for history. Reset scripts in the root (`reset_migration_db.py`, `reset_migration_state.sql`) can restore a clean state if needed.

## Logging & Monitoring

- `app/core/logger.py` configures console output plus daily-rotated log files under `logs/`.
- Application startup logs explicitly record database init success or surface the exception stack trace.
- Usage tracking middleware can be extended to emit metrics once a backend store is chosen.

## Testing (Manual for Now)

There is no active automated test suite. Recommended practices:

1. Use the interactive docs (`/docs`) to validate endpoints.
2. Seed sample data through SQL scripts or fixtures and hit API routes with `httpie`/`curl`.
3. Add unit tests under a future `tests/` package leveraging `pytest` and async test utilities.

## Deployment Considerations

- Set `ENVIRONMENT=production` to disable development shortcuts (e.g., Swagger auth persistence).
- Ensure database credentials enforce TLS (the engine appends `?ssl=require` by default).
- Provision monitored logging and metrics sinks (CloudWatch, Datadog, etc.) by replacing or extending the default logger.
- Rotate Clerk/OpenAI/AWS credentials via your runtime secrets manager.
- For container deployments, bake the environment variables into the orchestrator rather than embedding them in images.

## Extending the Service

- All RAG/Chroma vector database dependencies have been removed. If you reintroduce document retrieval, add new services and configuration explicitly.
- Background job hooks (`app/services/queue_scheduler.py`) remain as no-ops; re-enable with a proper scheduler if long-running jobs are reintroduced.
- Keep dependencies minimal and update `requirements.txt` alongside `frozen-requirements.txt` when upgrading.

---

For additional context on database resets, migrations, or historical scripts, review the helper files in the repository root (`MIGRATION_*.md`). These documents were preserved for operational reference.
