# Bitcoin Analysis

Bitcoin Analysis ingests public cryptocurrency and exchange-rate data into PostgreSQL, transforms it with dbt, and serves the results through a Next.js application.

No Railway project, service, database, schedule, or deployment has been created from this repository. Railway setup and production cutover remain manual operations.

The pre-migration Databricks configuration is retained in three disabled archives:

- `databricks.yml.disabled`
- `dbx_workflow/resources/master_orchestrator_job.yml.disabled`
- `app/vercel.json.disabled`

## Architecture

Production uses one private PostgreSQL service and two Railway services:

- The web service runs the Next.js application from `/app`.
- The daily Cron uses the repository root as its build and runtime context. The `raw-ingest` console command runs market ingestion, technical-indicator ingestion, then `dbt build`.
- Both services connect to the same private PostgreSQL database.
- GitHub Actions runs tests and builds only. It does not deploy to Railway or any other platform.

The Cron must keep the repository root as its context. The root `uv.lock` covers the workspace, including `dbx_workflow` and `dbt_silver_gold`. Setting the Cron root to `/dbx_workflow` would hide the dbt project.

## Railway and Railpack settings

Use Railpack for both services. Do not add a Dockerfile.

| Setting | Web | Daily Cron |
| --- | --- | --- |
| Root directory | `/app` | Repository root |
| Build command | `npm run build` | `uv sync --locked --package raw-ingest` |
| Start command | `npm run start` | `uv run --locked --package raw-ingest raw-ingest` |
| Watch paths | `app/**` | `dbx_workflow/**`, `dbt_silver_gold/**`, `pyproject.toml`, `uv.lock` |

Create exactly one Railway Cron schedule. Choose its UTC expression only after deciding how the intended Europe/Paris time should behave across daylight-saving changes.

### Variables

Keep PostgreSQL private and use Railway variable references.

| Service | Required variables |
| --- | --- |
| Web | `DATABASE_URL` |
| Daily Cron | `DATABASE_URL`, `DBT_TARGET_SCHEMA` |

The orchestrator derives `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`, and `PGDATABASE` from `DATABASE_URL` before it starts dbt. Database credentials are server-side only.

## Local setup

Required tools:

- Python 3.11
- uv 0.9.17
- Node.js 20 and npm
- PostgreSQL 16

Set `DATABASE_URL`, `TEST_DATABASE_URL`, `DBT_TARGET_SCHEMA`, and the `PG*` variables in the current shell. Do not commit local credentials.

Install and test the Python workspace from the repository root:

```powershell
uv sync --locked --package raw-ingest --extra dev
uv run --locked --package raw-ingest --extra dev pytest dbx_workflow/tests
uv run --locked --package raw-ingest dbt debug --project-dir dbt_silver_gold --profiles-dir dbt_silver_gold
uv run --locked --package raw-ingest dbt compile --project-dir dbt_silver_gold --profiles-dir dbt_silver_gold
uv run --locked --package raw-ingest dbt build --full-refresh --project-dir dbt_silver_gold --profiles-dir dbt_silver_gold
uv run --locked --package raw-ingest dbt build --project-dir dbt_silver_gold --profiles-dir dbt_silver_gold
```

Run the complete ingestion pipeline:

```powershell
uv run --locked --package raw-ingest raw-ingest
```

Install, test, and run the web application:

```powershell
Set-Location app
npm ci
npx tsc --noEmit
npm test -- --ci --watchAll=false --runInBand
npm run build
npm run dev
```

## Production cutover

Do not enable two schedulers against the same database.

1. Record the pre-migration Git tag or commit and keep it available for rollback.
2. Back up the current production database.
3. Restore that backup into a temporary PostgreSQL database. Test the restore, table counts, key queries, and application reads before proceeding.
4. Create the Railway PostgreSQL, web, and Cron services manually. Keep the Cron schedule disabled.
5. Configure the roots, Railpack commands, watch paths, and variables listed above.
6. Deploy the web and Cron services manually.
7. Disable the Databricks production schedule before the first Railway ingestion run. This step is mandatory.
8. Run the Railway Cron command once, then verify ingestion rows, dbt models, logs, and web reads.
9. Enable one Railway Cron schedule only after those checks pass.

## Rollback

1. Disable the Railway Cron schedule.
2. Redeploy the recorded pre-migration tag or commit.
3. Restore the tested backup if the cutover changed production data or schemas incompatibly.
4. Verify database reads and the previous pipeline before re-enabling its schedule.
5. Keep only one production scheduler active.

The backup is not a rollback plan until a restore has passed on a separate database.

## Continuous integration

`.github/workflows/ci.yml` uses Python 3.11, Node.js 20, and PostgreSQL 16. It runs:

- `uv lock --check`, then installs the Python workspace with `uv sync --locked`;
- raw-ingest tests with `TEST_DATABASE_URL`;
- dbt debug and compile, then `dbt build --full-refresh` followed by `dbt build` to check idempotence;
- `npm ci`, `npx tsc --noEmit`, Jest, and a production Next.js build.

CI only validates locks, tests, transformations, types, and builds. It creates no Railway infrastructure and performs no deployment.

`.github/workflows/daily_schema_check.yml` checks public API response schemas with Python 3.11 and opens a review pull request when generated Pydantic models change. It does not deploy the application.
