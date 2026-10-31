# Annotation Quality API

A small backend service that tracks **data-annotation tasks, submissions and reviews**, and reports
**quality metrics** (approval rate, rework rate, average score) per annotator and per project.

It models the review workflow used on AI data-labeling and evaluation projects: an annotator submits a
label for a task, a reviewer accepts it, asks for rework or rejects it, and the service keeps score.

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2 · Pydantic v2 · PostgreSQL (SQLite for local use) ·
pytest · Docker · GitHub Actions

## Features

- Annotators, tasks (grouped by project and guideline version), submissions and reviews
- A clear **review state machine**: `submitted → accepted | rework | rejected`
- A task can be submitted again **only after a "rework" review** (each retry increments `attempt`)
- A submission is reviewed **exactly once**
- Metrics per annotator and per project, computed in SQL
- Input validation (score `0–100`, decision enum) and consistent error responses (`404`, `409`, `422`)
- Interactive API docs at `/docs` (OpenAPI)

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

pytest -q                         # run the tests
uvicorn app.main:app --reload     # start the API on http://127.0.0.1:8000
```

Open <http://127.0.0.1:8000/docs> to try the endpoints.

### With Docker (PostgreSQL)

```bash
docker compose up --build
```

The API is then available on <http://localhost:8000>. The database URL is read from the `DATABASE_URL`
environment variable (SQLite is used when it is not set).

## Example workflow

```bash
# 1. create an annotator and a task
curl -X POST localhost:8000/annotators -H "Content-Type: application/json" -d '{"name": "alice"}'
curl -X POST localhost:8000/tasks -H "Content-Type: application/json" \
     -d '{"project": "sentiment", "prompt": "Label the sentiment of: I love this!"}'

# 2. the annotator submits a label
curl -X POST localhost:8000/submissions -H "Content-Type: application/json" \
     -d '{"task_id": 1, "annotator_id": 1, "content": "positive"}'

# 3. a reviewer decides: accepted | rework | rejected
curl -X POST localhost:8000/submissions/1/review -H "Content-Type: application/json" \
     -d '{"reviewer": "reviewer1", "decision": "accepted", "score": 95}'

# 4. read the quality metrics
curl localhost:8000/annotators/1/metrics
curl localhost:8000/projects/sentiment/metrics
```

Example metrics response:

```json
{
  "submissions": 4, "reviewed": 4,
  "accepted": 2, "rework": 1, "rejected": 1, "pending": 0,
  "approval_rate": 50.0, "rework_rate": 25.0, "average_score": 55.0
}
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/annotators` | Create an annotator |
| GET | `/annotators/{id}` | Read an annotator |
| GET | `/annotators/{id}/metrics` | Quality metrics for one annotator |
| POST | `/tasks` | Create a task |
| GET | `/tasks/{id}` | Read a task |
| POST | `/submissions` | Submit (or resubmit after rework) |
| GET | `/submissions/{id}` | Read a submission |
| POST | `/submissions/{id}/review` | Review a submission once |
| GET | `/projects/{project}/metrics` | Quality metrics for a project |
| GET | `/health` | Health check |

## Metric definitions

- **reviewed** = accepted + rework + rejected (pending submissions are not counted)
- **approval_rate** = accepted / reviewed × 100
- **rework_rate** = rework / reviewed × 100
- **average_score** = mean review score, `null` when nothing has been reviewed

## Project structure

```
app/
  main.py       application, error handlers, startup
  routes.py     HTTP endpoints
  services.py   business rules and metrics (no HTTP code)
  models.py     SQLAlchemy models
  schemas.py    Pydantic request/response models
  database.py   engine, session, DATABASE_URL handling
tests/          pytest suite (in-memory SQLite per test)
```

## Testing and CI

The tests cover the workflow rules (single review, resubmission only after rework), the metric
calculations and input validation. Every push and pull request runs `pytest` in GitHub Actions
(`.github/workflows/ci.yml`).

## Design notes

- Business rules live in `services.py`, so they can be tested without going through HTTP.
- Domain errors (`NotFoundError`, `ConflictError`) are translated to HTTP status codes in one place.
- Metrics are aggregated with SQL (`COUNT`, `AVG`) instead of loading rows into Python.
- A unique constraint on `(task_id, annotator_id, attempt)` protects the retry rule at database level.

## Roadmap

- Authentication and reviewer/annotator roles
- Database migrations with Alembic
- Pagination and filtering on list endpoints
- Metrics over time (weekly trends)

## Development notes

I designed the domain model and the review rules, and wrote the tests to match them. The code was
written with AI-assisted tooling and reviewed and run locally by me.
