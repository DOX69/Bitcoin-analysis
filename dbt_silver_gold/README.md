Welcome to your new dbt project!

### Development and Testing

Before running DBT commands, make sure your Python environment is synchronized. From the root of the repository, run:
```bash
uv sync
```

Then, from within this `dbt_silver_gold` directory, try running the following commands:
- `uv run dbt deps`
- `uv run dbt run`
- `uv run dbt test`

> **Note**: If `dbt run` fails with `[DELTA_UNSUPPORTED_DROP_COLUMN]`, try using the `--full-refresh` flag (e.g., `uv run dbt run --full-refresh`) to rebuild the tables from scratch.


### Resources:
- Learn more about dbt [in the docs](https://docs.getdbt.com/docs/introduction)
- Check out [Discourse](https://discourse.getdbt.com/) for commonly asked questions and answers
- Join the [chat](https://community.getdbt.com/) on Slack for live discussions and support
- Find [dbt events](https://events.getdbt.com) near you
- Check out [the blog](https://blog.getdbt.com/) for the latest news on dbt's development and best practices
