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
{{ 
            config(
                materialized='incremental',
                unique_key='date_indicators',
                on_schema_change='sync_all_columns'
                ) 
        }}
with source_rows as (
    select
        d,
        macd,
        macdsignal,
        macdhist,
        sma7,
        sma50,
        sma200,
        ema7,
        ema50,
        ema200,
        ingest_date_time
    from {{ source('bronze', 'bgeometrics_btc_technical_indicators') }}
    {% if is_incremental() %}
    where ingest_date_time > (select max(ingest_date_time) from {{ this }})
    {% endif %}
), ranked as (
    select
        *,
        row_number() over (partition by d order by ingest_date_time desc) as row_number
    from source_rows
), deduplicated as (
    select *
    from ranked
    where row_number = 1
)
select
    d as date_indicators,
    {% for src, alias in indicators %}
    round({{ src }}::numeric, 2)::double precision as {{ alias }},
    {% endfor %}
    current_timestamp::timestamp without time zone as ingest_date_time,
    '{{ invocation_id }}' as dbt_batch_id
from deduplicated
