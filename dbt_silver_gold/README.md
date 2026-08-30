# Silver and gold dbt models

This dbt project targets PostgreSQL. Its profile reads connection settings from
the environment; it contains no credentials.

Required variables:

- `PGHOST`
- `PGPORT`
- `PGUSER`
- `PGPASSWORD`
- `PGDATABASE`
- `DBT_TARGET_SCHEMA`

Run from this directory:

```powershell
uv sync
uv run dbt debug --profiles-dir .
uv run dbt compile --profiles-dir .
uv run dbt build --profiles-dir .
```

The integration fixtures in `tests/fixtures/setup.sql` target a disposable
PostgreSQL database. They do not call external APIs.

`DBT_TARGET_SCHEMA` controls dbt's own connection schema. The
`generate_schema_name` macro intentionally keeps the application schemas stable
as `dlh_silver__*` and `dlh_gold__*`. Railway environments therefore require
separate PostgreSQL databases for isolation.
