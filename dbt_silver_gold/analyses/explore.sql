
{% set period = 14 %}

    WITH price_changes AS (
        SELECT *,
            close,
            LAG(close) OVER (ORDER BY date) AS prev_price,
            close - prev_price AS change
        from {{ source('bronze', 'btc_usd_ohlcv') }}
    ),
    gains_losses AS (
        SELECT * ,
            CASE WHEN change > 0 THEN change ELSE 0 END AS gain,
            CASE WHEN change < 0 THEN -change ELSE 0 END AS loss,
            AVG(CASE WHEN change > 0 THEN change ELSE 0 END) OVER (
                ORDER BY date ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW
            ) AS avg_gain,
            AVG(CASE WHEN change < 0 THEN -change ELSE 0 END) OVER (
                ORDER BY date ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW
            ) AS avg_loss
        FROM price_changes
    )
    SELECT
        *,ROUND(100 - (100 / (1 + (avg_gain / NULLIF(avg_loss, 0)))), 2) AS rsi
    FROM gains_losses
    order by date desc