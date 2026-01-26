{% set period = 14 %}
{% set column = 'close' %}
WITH price_changes AS (
        SELECT *,
            ROW_NUMBER() OVER (PARTITION BY DATE ORDER BY ingest_date_time desc) AS rn,
            {{ previous_price_change(column) }} AS change
        from {{ source('bronze', 'btc_usd_ohlcv') }}
            qualify rn = 1
    ),
    get_rsi AS (
        SELECT *,
            {{ rsi('change', period) }}
        FROM price_changes
    )
SELECT * except (avg_gain, avg_loss, rn, change, rsi_calculated)
FROM get_rsi
order by date desc
