{# comment for now since we are only ingesting BTC #}
{# {{ create_update_obt_fact_day_crypto('bronze', 'eth_usd_ohlcv') }} #}
SELECT
  cast(null as date) as date_prices,
  cast(null as double precision) as low_usd,
  cast(null as double precision) as high_usd,
  cast(null as double precision) as open_usd,
  cast(null as double precision) as close_usd,
  cast(null as double precision) as volume,
  cast(null as double precision) as rsi,
  cast(null as text) as rsi_status,
  cast(null as double precision) as rate_usd_chf,
  cast(null as double precision) as rate_usd_eur,
  cast(null as double precision) as low_chf,
  cast(null as double precision) as high_chf,
  cast(null as double precision) as open_chf,
  cast(null as double precision) as close_chf,
  cast(null as double precision) as low_eur,
  cast(null as double precision) as high_eur,
  cast(null as double precision) as open_eur,
  cast(null as double precision) as close_eur,
  cast(null as timestamp without time zone) as ingest_date_time,
  cast(null as text) as dbt_batch_id
LIMIT 0
