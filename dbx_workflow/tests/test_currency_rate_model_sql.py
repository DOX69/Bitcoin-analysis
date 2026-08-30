from pathlib import Path


MODEL_PATH = (
    Path(__file__).parents[2]
    / "dbt_silver_gold"
    / "models"
    / "silver"
    / "currency_rate"
    / "usd_to_other.sql"
)


def test_incremental_filter_keeps_calendar_and_fresh_source_branches():
    sql = MODEL_PATH.read_text(encoding="utf-8")

    assert "date_rates > coalesce((select max(date_rates) from {{ this }})" in sql
    assert "date_rates >= current_date - interval '10 days'" in sql
    assert "ingest_date_time > (select max(update_date_time) from {{ this }})" in sql
