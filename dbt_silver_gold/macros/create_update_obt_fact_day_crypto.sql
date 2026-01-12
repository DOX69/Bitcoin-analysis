{% macro create_update_obt_fact_day_crypto(source_schema_name, source_table_name) %}
    {{ 
        config(
            materialized='incremental',
            unique_key='date_prices'
            ) 
    }}

    with increment_data as (

            select date as date_prices,
            * except (date, time) 
            from {{ source(source_schema_name, source_table_name) }}

            {% if is_incremental() %}
            where ingest_date_time > (select max(ingest_date_time) from {{ this }})
            {% endif %}

        )
        , deduplicate_data as (
            select *, row_number() over (partition by date_prices order by ingest_date_time desc) as rn
            from increment_data
                qualify rn = 1
        )

    select * except (rn),
        '{{ invocation_id }}' as dbt_batch_id
    from deduplicate_data
{% endmacro %}