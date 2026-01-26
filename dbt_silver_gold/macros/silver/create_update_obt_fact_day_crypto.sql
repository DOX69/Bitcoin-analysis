{% macro create_update_obt_fact_day_crypto(source_schema_name, source_table_name) %}
{{ 
            config(
                materialized='incremental',
                unique_key='date_prices',
                on_schema_change='sync_all_columns'
                ) 
        }}

{% set period = 14 %}

with deduplicate as (
        select *, row_number() over (partition by date order by ingest_date_time desc) as rn
        from {{ source(source_schema_name, source_table_name) }}
            qualify rn = 1
    )
    -- RSI Calculation
    , add_previous_price_change as (
        select *,
            {{ previous_price_change('close') }} AS change
        from deduplicate
    )
    , add_rsi as (
        select *,
            {{ rsi('change', period) }}
        from add_previous_price_change
    )
    -- Incremental Load Step
    , increment_data as (

        select date as date_prices,
            * except (date, time,avg_gain, avg_loss, rn, change, rsi_calculated)
        from add_rsi

            {% if is_incremental() %}
        where ingest_date_time > (select max(ingest_date_time) from {{ this }})
            {% endif %}

    )
select * except (ingest_date_time),
     current_timestamp as ingest_date_time,
    '{{ invocation_id }}' as dbt_batch_id
from increment_data
    {% endmacro %}