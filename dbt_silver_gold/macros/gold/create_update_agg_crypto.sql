{%- macro create_update_agg(table_source, granularity) -%}
{{ 
            config(
                materialized='incremental',
                unique_key='iso_week_start_date',
                on_schema_change='sync_all_columns'
                ) 
        }}

{%- if granularity == "week" -%}
    {%- set agg_cols = "iso_week_start_date, month_start_date, quarter_start_date, year_start_date" -%}
    {%- set parition_by_col = "iso_week_start_date" -%}
    {%- set order_by_col = "date_prices" -%}
    
{%- elif granularity == "month" %}
    {%- set agg_cols = "month_start_date, quarter_start_date, year_start_date" -%}
    {%- set parition_by_col = "month_start_date" -%}
    {%- set order_by_col = "iso_week_start_date" -%}

{%- endif -%}

With join_calendar as (
        select ingest_date_time,

        {%- if granularity == "week" -%}
        date_prices,
        {%- endif -%}

        low,
        high,
        open,
        close,
        {{agg_cols}}        
    from {{table_source}} ofdb 
    {% if granularity == "week" %}
        left join {{ source('silver', 'dim_calendar') }} as dc on ofdb.date_prices = dc.date
    {% endif %}
    )
    ,open_close as (
        select
        date_prices,
        {{agg_cols}},
        low,
        high,
        first(open) over(partition by {{parition_by_col}} order by {{order_by_col}} asc ) as open,
        first(close) over(partition by {{parition_by_col}} order by {{order_by_col}} desc) as close,
        ingest_date_time
        from join_calendar
    )
    ,agg as (
    select 
        {{agg_cols}},
        min(low) as low,
        max(high) as high,
        max(open) as open,
        max(close) as close,
        max(ingest_date_time) as ingest_date_time
        from open_close
    group by ALL
    )
    ,increment_data as (
    select * from agg
    {% if is_incremental() %}
      where ingest_date_time >= (select max(ingest_date_time) from {{ this }})
    {% endif %}
    )
    select *  except (ingest_date_time),
    current_timestamp as ingest_date_time,
    '{{ invocation_id }}' as dbt_batch_id
    from increment_data
{% endmacro %}