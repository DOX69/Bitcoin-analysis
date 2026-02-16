Welcome to your new dbt project!

### Using the starter project

Try running the following commands:
- dbt run
- dbt test


### Resources:
- Learn more about dbt [in the docs](https://docs.getdbt.com/docs/introduction)
- Check out [Discourse](https://discourse.getdbt.com/) for commonly asked questions and answers
- Join the [chat](https://community.getdbt.com/) on Slack for live discussions and support
- Find [dbt events](https://events.getdbt.com) near you
- Check out [the blog](https://blog.getdbt.com/) for the latest news on dbt's development and best practices

### Reproduction Steps
To reproduce the `dbt test` execution:
1. Navigate to the project directory:
   ```bash
   cd dbt_silver_gold
   ```
2. Activate the virtual environment:
   ```bash
   source .venv/Scripts/activate
   ```
3. Build the models (required for fresh setup or after changes):
   ```bash
   dbt run --full-refresh
   ```
4. Run the tests:
   ```bash
   dbt test
   ```

### Development Workflow & CI/CD

#### 1. Feature Development
When developing new features or optimizing models:
1.  **Switch to a new branch**: `git checkout -b feature/my-new-feature`
2.  **Develop in Dev**: working against your `dev` target.
3.  **Compile Frequently**: Ensure your SQL is valid and macros expand correctly.
    ```bash
    dbt compile --select <my_model>
    ```
4.  **Test Incrementally**: If modifying incremental models (like `obt_fact_day_btc`), verify both full refresh and incremental logic.
    -   **Full Refresh**: `dbt run --full-refresh --select <my_model>`
    -   **Incremental**: `dbt run --select <my_model>` (ensure it runs fast!)

#### 2. Performance Verification (EMA Models)
For models using complex logic like `obt_fact_day_btc` (EMA calculation), always verify performance:
1.  **Check Execution Time**: Incremental runs should be significantly faster than full refreshes.
2.  **Verify Data Continuity**: Ensure no gaps or jumps in calculated values at the boundary of updates.
    ```sql
    -- Example check in Databricks/Spark
    select date_prices, ema_9 
    from silver.obt_fact_day_btc 
    order by date_prices desc 
    limit 10;
    ```

#### 3. CI/CD Pipeline
The project produces a robust CI/CD pipeline:
1.  **Pull Request**: When you push a branch and open a PR, the CI pipeline triggers.
2.  **Linting**: SQL code is linted for best practices.
3.  **Compilation**: dbt compiles the project to ensure structural integrity.
4.  **Testing**: `dbt test` runs to valid data quality.
5.  **Merge**: Once all checks pass, merge to `main` for deployment to Production.
