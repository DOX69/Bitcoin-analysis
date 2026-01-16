{%- macro rsi(column_change,period,date_column='date') -%}
AVG(CASE WHEN {{ column_change }} > 0 THEN {{ column_change }} ELSE 0 END) OVER (
    ORDER BY {{ date_column }} ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW
) AS avg_gain,
AVG(CASE WHEN {{ column_change }} < 0 THEN -{{ column_change }} ELSE 0 END) OVER (
    ORDER BY {{ date_column }} ROWS BETWEEN {{ period - 1 }} PRECEDING AND CURRENT ROW
) AS avg_loss,
ROUND(100 - (100 / (1 + (avg_gain / NULLIF(avg_loss, 0)))), 2) AS rsi_calculated,
CASE WHEN rsi_calculated BETWEEN 0 AND 100 THEN rsi_calculated ELSE NULL END AS rsi,
CASE
    WHEN rsi_calculated < 30 THEN 'oversold'
    WHEN rsi_calculated > 70 THEN 'overbought'
    ELSE 'neutral'
END AS rsi_status
{%- endmacro -%}
