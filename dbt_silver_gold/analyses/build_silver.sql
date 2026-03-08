{%- set indicators = [
    ('macd', 'macd'),
    ('macdsignal', 'macd_signal'),
    ('macdhist', 'macd_hist'),
    ('sma7', 'sma_7'),
    ('sma50', 'sma_50'),
    ('sma200', 'sma_200'),
    ('ema7', 'ema_7'),
    ('ema50', 'ema_50'),
    ('ema200', 'ema_200')
] -%}
with source as (
    select * from {{ source('bronze', 'bgeometrics_btc_technical_indicators') }}
)


select 
d as date_indicators,
{% for src, alias in indicators %}
round({{src}}, 2) as {{alias}},
{% endfor %}
current_timestamp as ingest_date_time
from source
