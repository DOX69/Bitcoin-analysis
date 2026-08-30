# Bitcoin Analysis

Bitcoin Analysis collects public Bitcoin OHLCV, exchange-rate, and technical-indicator data. It stores the raw data in PostgreSQL, transforms it with dbt, and serves the dashboard through Next.js on Railway.

## Production

- Production dashboard: <https://bitcoin-web-prod-production.up.railway.app/dashboard>
- Development dashboard: <https://bitcoin-web-development.up.railway.app/dashboard>
- GitHub default branch: `main`
- Production ingestion schedule: `0 1 * * *` (01:00 UTC)

Railway is the production platform. Vercel is not part of the deployment path.

## Architecture

The Railway project has separate Development and production environments. Each environment contains a PostgreSQL service, a Next.js web service, and a Python/dbt ingestion service.

Production services are:

- `bitcoin-web-prod`: Next.js web application, using `/app` as its root directory.
- `bitcoin-cron-prod`: daily ingestion service, using the repository root so it can access both `dbx_workflow` and `dbt_silver_gold`.
- `Postgres-r3OB`: private PostgreSQL database.

The web service is built and started by Railpack from the Next.js package scripts. The ingestion service runs `raw-ingest`, which fetches market prices and technical indicators before running the dbt build. The orchestrator derives the `PG*` variables from `DATABASE_URL` before invoking dbt.

Keep the production cron as the only production scheduler. Do not move the cron root directory to `/dbx_workflow`; that would hide the dbt project and the root workspace lockfile.

The old Databricks configuration remains only as disabled files:

- `databricks.yml.disabled`
- `dbx_workflow/resources/master_orchestrator_job.yml.disabled`

These files are not part of the active runtime.

## Railway configuration

| Setting | Web service | Daily cron |
| --- | --- | --- |
| Root directory | `/app` | Repository root |
| Build | Railpack detects `npm run build` | `uv sync --locked --package raw-ingest` |
| Start | Railpack detects `npm run start` | `uv run --locked --package raw-ingest raw-ingest` |
| Schedule | None | `0 1 * * *` |

Required Railway variables:

| Service | Variables |
| --- | --- |
| Web | `DATABASE_URL` |
| Daily cron | `DATABASE_URL`, `DBT_TARGET_SCHEMA` |

Database credentials stay server-side. Do not commit `.env` files or credentials.

## Repository layout

- `app/`: Next.js dashboard and API route.
- `dbx_workflow/`: Python fetchers, ingestion services, PostgreSQL writer, and tests.
- `dbt_silver_gold/`: dbt project, models, macros, and data tests.
- `example_response_api_data/`: example external API payloads.
- `.github/workflows/`: CI and scheduled API schema checks.

## Local setup

Required tools:

- Python 3.11
- uv 0.9.17 or a compatible newer version
- Node.js 20 and npm
- PostgreSQL 16

Set `DATABASE_URL`, `TEST_DATABASE_URL`, `DBT_TARGET_SCHEMA`, and the `PG*` variables in the current shell. Use local values only and keep them out of Git.

From the repository root:

```powershell
uv sync --locked --package raw-ingest --extra dev
uv run --locked --package raw-ingest --extra dev pytest dbx_workflow/tests
uv run --locked --package raw-ingest dbt debug --project-dir dbt_silver_gold --profiles-dir dbt_silver_gold
uv run --locked --package raw-ingest dbt compile --project-dir dbt_silver_gold --profiles-dir dbt_silver_gold
uv run --locked --package raw-ingest dbt build --full-refresh --project-dir dbt_silver_gold --profiles-dir dbt_silver_gold
uv run --locked --package raw-ingest dbt build --project-dir dbt_silver_gold --profiles-dir dbt_silver_gold
```

Run the complete ingestion pipeline with:

```powershell
uv run --locked --package raw-ingest raw-ingest
```

Run the web application with:

```powershell
Set-Location app
npm ci
npx tsc --noEmit
npm run lint
npm test -- --ci --watchAll=false --runInBand
npm run build
npm run dev
```

The local dashboard is available at <http://localhost:3000/dashboard>.

## Continuous integration

`.github/workflows/ci.yml` runs on pushes to all branches. It provisions PostgreSQL 16, verifies the Python lockfile, runs the Python tests, prepares dbt fixtures, compiles and builds dbt twice, then installs and validates the Next.js application with typecheck, lint, Jest, and a production build.

`.github/workflows/daily_schema_check.yml` runs every day and can be started manually. It compares the public Coinbase, BGeometrics, and Frankfurter response shapes with the checked-in Pydantic models. When models change, it opens a pull request. It does not deploy the application.

## Deployment and rollback

Railway deploys the web and ingestion services from `main`. After a production deployment, verify the dashboard URL, the web service health, PostgreSQL reads, and the next cron schedule.

To roll back:

1. Disable the production cron.
2. Deploy a known-good commit to the affected Railway service.
3. Verify the application and database reads.
4. Re-enable the cron only after the web and data paths are healthy.

A database backup is part of rollback only after a restore has been tested on a separate database.
