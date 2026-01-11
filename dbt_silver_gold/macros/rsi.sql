{% macro rsi(column, period) %}
    WITH price_changes AS (
        SELECT
            {{ column }},
            LAG({{ column }}) OVER (ORDER BY date) AS prev_price,
            {{ column }} - LAG({{ column }}) OVER (ORDER BY date) AS change
        FROM {{ this }}
    ),
    gains_losses AS (
        SELECT
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
        ROUND(100 - (100 / (1 + (avg_gain / NULLIF(avg_loss, 0)))), 2) AS rsi
    FROM gains_losses
{% endmacro %}