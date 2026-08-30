# Raw ingestion and orchestration

`raw-ingest` loads cryptocurrency prices, exchange rates, and Bitcoin technical
indicators into PostgreSQL. The same process then runs the
`dbt_silver_gold` transformations.

## Orchestrator

The `raw-ingest` console command runs one pipeline:

1. Connect to `DATABASE_URL` and acquire a PostgreSQL advisory lock.
2. Ingest BTC/USD, ETH/USD, USD/EUR, and USD/CHF market data.
3. Ingest Bitcoin technical indicators.
4. Run:

   ```powershell
   uv run --locked --project dbx_workflow dbt build --project-dir dbt_silver_gold --profiles-dir dbt_silver_gold
   ```

The ingestion stages share one run ID. A second process exits with status 1 while
the advisory lock is held. Any stage failure also returns status 1, skips the
remaining stages, and releases the lock.

## PostgreSQL variables

The process requires:

- `DATABASE_URL`, a PostgreSQL connection URL used by the ingestors.
- `DBT_TARGET_SCHEMA`, the dbt connection schema.

Before dbt starts, the orchestrator derives `PGHOST`, `PGPORT`, `PGUSER`,
`PGPASSWORD`, and `PGDATABASE` from `DATABASE_URL`. It also forwards
`sslmode` as `PGSSLMODE` when the URL includes it.

Keep credentials in the local shell or Railway variables. Do not store them in
the repository.

## Local development

Run commands from the repository root so both `dbx_workflow` and
`dbt_silver_gold` are available:

```powershell
uv sync --locked --project dbx_workflow --extra dev
uv run --locked --project dbx_workflow pytest dbx_workflow/tests
uv run --locked --project dbx_workflow raw-ingest
```

Database-backed tests use `TEST_DATABASE_URL`.

## Railway Cron

Use the repository root as the Railway service root. The sibling dbt project is
not available if the service root is `/dbx_workflow`.

Suggested Railpack commands:

- Build: `uv sync --locked --project dbx_workflow`
- Start: `uv run --locked --project dbx_workflow raw-ingest`

Set `DATABASE_URL` with a reference to the private Railway PostgreSQL service,
and set `DBT_TARGET_SCHEMA` on the Cron service. Keep exactly one production
scheduler active.

The former Databricks job definition is archived as
`resources/master_orchestrator_job.yml.disabled`. It is retained for reference
and is not an active bundle resource.
