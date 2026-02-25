{# comment for now since we are only ingesting BTC #}
{# {{ create_update_obt_fact_day_crypto('bronze', 'eth_usd_ohlcv') }} #}
SELECT
  cast(null as date) as date_prices,
  cast(null as double) as low_usd,
  cast(null as double) as high_usd,
  cast(null as double) as open_usd,
  cast(null as double) as close_usd,
  cast(null as double) as volume,
  cast(null as double) as rsi,
  cast(null as string) as rsi_status,
  cast(null as double) as rate_usd_chf,
  cast(null as double) as rate_usd_eur,
  cast(null as double) as low_chf,
  cast(null as double) as high_chf,
  cast(null as double) as open_chf,
  cast(null as double) as close_chf,
  cast(null as double) as low_eur,
  cast(null as double) as high_eur,
  cast(null as double) as open_eur,
  cast(null as double) as close_eur,
  cast(null as timestamp) as ingest_date_time,
  cast(null as string) as dbt_batch_id
LIMIT 0