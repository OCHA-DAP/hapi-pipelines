# HAPI Pipelines

Humanitarian data pipeline system that ingests data from HDX (Humanitarian Data Exchange) into a PostgreSQL database for the OCHA HAPI (Humanitarian API) project.

## Architecture

**Entry point:** `src/hapi/pipelines/app/__main__.py`

**Main orchestrator:** `src/hapi/pipelines/app/pipelines.py` — the `Pipelines` class coordinates all sub-pipelines. Each pipeline is a domain-specific uploader (population, food security, funding, conflict, etc.) in `src/hapi/pipelines/database/`.

**Uploader hierarchy:**
- `BaseUploader` — abstract base with `populate()` interface
- `HapiBasicUploader` — simple table populations from HDX datasets
- `HapiSubcategoryUploader` — tables with location/admin hierarchies

**Configuration:** YAML files in `configs/` (core.yaml, national_risk.yaml, wfp.yaml) loaded at startup via `app/__init__.py`.

**Key external libraries:**
- `hapi-schema` — SQLAlchemy ORM models for the HAPI database schema
- `hdx-python-api` — fetching datasets from HDX
- `hdx-python-pipelineutils` — reader abstraction over data sources
- `hdx-python-database` — database connection/session management

## Running

```bash
# Default (SQLite hapi.db)
python -m hapi.pipelines.app

# PostgreSQL
python -m hapi.pipelines.app --db "postgresql+psycopg://postgres:postgres@localhost:5432/hapi"

# Filter to specific themes (optionally by country)
python -m hapi.pipelines.app --themes population funding
python -m hapi.pipelines.app --themes population:AFG|COD
```

## Tests

```bash
pytest
# or
hatch test
```

Tests use `--save`/`--use-saved` fixtures to avoid live HDX calls. Saved data lives in `saved_data/`.

## Linting and Formatting

```bash
ruff check --fix   # lint
ruff format        # format
```

Pre-commit hooks run ruff automatically. Config in `ruff.toml` (E, F, I rules; E501 ignored).

## Scope of Changes

When fixing a bug or addressing PR feedback, change only what is necessary to resolve the specific issue. Do not refactor surrounding code, rename variables, adjust formatting, or make improvements in the same commit unless they are directly required by the fix. Unrelated changes obscure the intent of the fix and complicate review and blame.
