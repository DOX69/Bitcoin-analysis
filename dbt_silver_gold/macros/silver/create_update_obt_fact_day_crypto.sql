{% macro create_update_obt_fact_day_crypto(source_schema_name, source_table_name) %}
{{ 
            config(
                materialized='incremental',
                unique_key='date_prices',
                on_schema_change='sync_all_columns'
                ) 
        }}

{% set period = 14 %}

with deduplicate_source as (
        select *, row_number() over (partition by date order by ingest_date_time desc) as rn
        from {{ source(source_schema_name, source_table_name) }}
            qualify rn = 1
    )
    , rates as (
        select date_rates,
        rate_usd_chf,
        rate_usd_eur
        from {{ ref('usd_to_other') }}
    )
    -- RSI Calculation
    , add_previous_price_change as (
        select *,
            {{ previous_price_change('close') }} AS change
        from deduplicate_source
    )
    , add_rsi as (
        select *,
            {{ rsi('change', period) }}
        from add_previous_price_change
    )
    -- EMA Calculation (9/21/55) using recursive CTE
    , {{ ema('add_rsi', 'close', 'date') }}
    , add_ema_signals as (
        select *,
            {{ ema_status('close', 'date') }}
        from ema_recursive
    )
    -- Incremental Load Step
    , increment_filter as (

        select date as date_prices,
            * except (date, time, avg_gain, avg_loss, rn, change, rsi_calculated, _ema_rn)
        from add_ema_signals

            {% if is_incremental() %}
        where ingest_date_time > (select max(ingest_date_time) from {{ this }})
            {% endif %}

    )
    ,increment_data as (
select * except (ingest_date_time),
     current_timestamp as ingest_date_time,
    '{{ invocation_id }}' as dbt_batch_id
from increment_filter
    )
    select date_prices,
    low as low_usd,
    high as high_usd,
    open as open_usd,
    close as close_usd,
    volume,
    rsi,
    rsi_status,
    ema_9,
    ema_21,
    ema_55,
    ema_100,
    ema_150,
    ema_200,
    ema_status,
    ema_signal,
    rate_usd_chf,
    rate_usd_eur,
    round(low * rate_usd_chf, 2) as low_chf,
    round(high * rate_usd_chf, 2) as high_chf,
    round(open * rate_usd_chf, 2) as open_chf,
    round(close * rate_usd_chf, 2) as close_chf,
    round(low * rate_usd_eur, 2) as low_eur,
    round(high * rate_usd_eur, 2) as high_eur,
    round(open * rate_usd_eur, 2) as open_eur,
    round(close * rate_usd_eur, 2) as close_eur,
    ingest_date_time,
    dbt_batch_id
    from increment_data as id left join rates as r
    on r.date_rates = id.date_prices
    {% endmacro %}