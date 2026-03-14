{% macro create_update_obt_fact_day_crypto(source_schema_name, source_table_name) %}
{{ 
            config(
                materialized='incremental',
                unique_key='date_prices',
                on_schema_change='sync_all_columns'
                ) 
        }}

{% set period = 14 %}
{% set currencies = ['chf', 'eur'] %}
{% set cols_ohlc = ['low', 'high', 'open', 'close'] %}
{% set cols_technical_indicators = ['macd', 'macd_signal', 'macd_hist', 'sma_7', 'sma_50', 'sma_200', 'ema_7', 'ema_50', 'ema_200'] %}
{% set cols_to_convert_currency = cols_ohlc + cols_technical_indicators %}

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
    -- Incremental Load Step
    , increment_filter as (

        select date as date_prices,
            * except (date, time,avg_gain, avg_loss, rn, change, rsi_calculated)
        from add_rsi

            {% if is_incremental() %}
        where ingest_date_time > (select max(ingest_date_time) - INTERVAL '10' DAY from {{ this }})
            {% endif %}

    )
    -- add bgeometrics_technical_indicators
    , add_technical_indicators as (
        select if.*, fb.* except (fb.date_indicators, fb.ingest_date_time, fb.dbt_batch_id)
        from increment_filter as if
        left join {{ ref('fact_btc') }} as fb
        on if.date_prices = fb.date_indicators
    )
    ,increment_data as (
select * except (ingest_date_time),
     current_timestamp as ingest_date_time,
    '{{ invocation_id }}' as dbt_batch_id
from add_technical_indicators
    )
    select date_prices,
    {%- for col in cols_to_convert_currency %}
    {{ col }} as {{ col }}_usd,
    {%- endfor %}
    volume,
    rsi,
    rsi_status,
    rate_usd_chf,
    rate_usd_eur,
    {%- for curr in currencies -%}
        {%- for col in cols_to_convert_currency -%}
    round({{ col }} * rate_usd_{{ curr }}, 2) as {{ col }}_{{ curr }},
        {%- endfor -%}
    {%- endfor %}
    ingest_date_time,
    dbt_batch_id
    from increment_data as id left join rates as r
    on r.date_rates = id.date_prices
{% endmacro %}