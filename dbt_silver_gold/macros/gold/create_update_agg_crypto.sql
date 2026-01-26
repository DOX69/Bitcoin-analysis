{%- macro create_update_agg(table_source, granularity) -%}
{% set period = 14 %}

{%- if granularity == "week" -%}
    {%- set smaller_granularity_ref_col = "date_prices" -%}
    {%- set agg_cols = "iso_week_start_date, month_start_date, quarter_start_date, year_start_date" -%}
    {%- set parition_by_col = "iso_week_start_date" -%}
    
{%- elif granularity == "month" %}
    {%- set smaller_granularity_ref_col = "iso_week_start_date" -%}
    {%- set agg_cols = "month_start_date, quarter_start_date, year_start_date" -%}
    {%- set parition_by_col = "month_start_date" -%}
    
{%- elif granularity == "quarter" %}
    {%- set smaller_granularity_ref_col = "month_start_date" -%}
    {%- set agg_cols = "quarter_start_date, year_start_date" -%}
    {%- set parition_by_col = "quarter_start_date" -%}
    
{%- elif granularity == "year" %}
    {%- set smaller_granularity_ref_col = "quarter_start_date" -%}
    {%- set agg_cols = "year_start_date" -%}
    {%- set parition_by_col = "year_start_date" -%}

{%- endif -%}


{{ 
    config(
        materialized='incremental',
        unique_key=parition_by_col,
        on_schema_change='sync_all_columns'
        ) 
}}

With join_calendar as (
        select ingest_date_time,

        {{smaller_granularity_ref_col}},

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

        {{smaller_granularity_ref_col}},
        {{agg_cols}},

        low,
        high,
        first(open) over(partition by {{parition_by_col}} order by {{smaller_granularity_ref_col}} asc ) as open,
        first(close) over(partition by {{parition_by_col}} order by {{smaller_granularity_ref_col}} desc) as close,
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
    ,add_previous_price_change as (
        select *,
            {{ previous_price_change('close', parition_by_col) }} AS change
        from agg
    )
    ,add_rsi as (
        select *,
            {{ rsi('change', period, parition_by_col) }}
        from add_previous_price_change
    )
    ,increment_data as (
    select * from add_rsi
    {% if is_incremental() %}
      where ingest_date_time >= (select max(ingest_date_time) from {{ this }})
    {% endif %}
    )
    select *  except (ingest_date_time, avg_gain, avg_loss, change, rsi_calculated),
    current_timestamp as ingest_date_time,
    '{{ invocation_id }}' as dbt_batch_id
    from increment_data
{% endmacro %}
