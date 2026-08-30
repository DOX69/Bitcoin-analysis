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
{% set ohlc_columns = ['low', 'high', 'open', 'close'] %}
{% set technical_columns = ['macd', 'macd_signal', 'macd_hist', 'sma_7', 'sma_50', 'sma_200', 'ema_7', 'ema_50', 'ema_200'] %}
{% set converted_columns = ohlc_columns + technical_columns %}

with ranked_source as (
    select
        date,
        low,
        high,
        open,
        close,
        volume,
        ingest_date_time,
        row_number() over (partition by date order by ingest_date_time desc) as row_number
    from {{ source(source_schema_name, source_table_name) }}
), deduplicated_source as (
    select date, low, high, open, close, volume, ingest_date_time
    from ranked_source
    where row_number = 1
), add_previous_price_change as (
    select
        *,
        {{ previous_price_change('close') }} as change
    from deduplicated_source
), add_rsi as (
    select
        *,
        {{ rsi('change', period) }}
    from add_previous_price_change
), increment_filter as (
    select
        date as date_prices,
        low,
        high,
        open,
        close,
        volume,
        rsi,
        rsi_status
    from add_rsi
    {% if is_incremental() %}
    where ingest_date_time > (
        select max(ingest_date_time) - interval '10 days'
        from {{ this }}
    )
    {% endif %}
), add_technical_indicators as (
    select
        prices.date_prices,
        prices.low,
        prices.high,
        prices.open,
        prices.close,
        prices.volume,
        prices.rsi,
        prices.rsi_status,
        indicators.macd,
        indicators.macd_signal,
        indicators.macd_hist,
        indicators.sma_7,
        indicators.sma_50,
        indicators.sma_200,
        indicators.ema_7,
        indicators.ema_50,
        indicators.ema_200
    from increment_filter as prices
    left join {{ ref('fact_btc') }} as indicators
        on prices.date_prices = indicators.date_indicators
)
select
    prices.date_prices,
    {% for column in converted_columns %}
    prices.{{ column }}::double precision as {{ column }}_usd,
    {% endfor %}
    prices.volume::double precision as volume,
    prices.rsi::double precision as rsi,
    prices.rsi_status,
    rates.rate_usd_chf::double precision as rate_usd_chf,
    rates.rate_usd_eur::double precision as rate_usd_eur,
    {% for currency in currencies %}
        {% for column in converted_columns %}
    round((prices.{{ column }} * rates.rate_usd_{{ currency }})::numeric, 2)::double precision as {{ column }}_{{ currency }},
        {% endfor %}
    {% endfor %}
    current_timestamp::timestamp without time zone as ingest_date_time,
    '{{ invocation_id }}' as dbt_batch_id
from add_technical_indicators as prices
left join {{ ref('usd_to_other') }} as rates
    on rates.date_rates = prices.date_prices
{% endmacro %}
