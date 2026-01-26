{%- macro create_update_agg(table_source, granularity) -%}
{% set period = 14 %}
{%- set currencies = ["usd", "chf", "eur"] -%}
{%- set ohlc_configs = [] -%}

{%- for cur in currencies -%}
  {%- if cur == "" -%}
    {%- set cfg = {
      "low": "low",
      "high": "high",
      "open": "open",
      "close": "close"
    } -%}
  {%- else -%}
    {# string concatenation using the ~ operator #}
    {%- set suffix = "_" ~ cur -%}
    {%- set cfg = {
      "low": "low" ~ suffix,
      "high": "high" ~ suffix,
      "open": "open" ~ suffix,
      "close": "close" ~ suffix
    } -%}
  {%- endif -%}

  {%- do ohlc_configs.append(cfg) -%}
{%- endfor -%}


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
        {% for cfg in ohlc_configs %}
            {{ cfg.low }},
            {{ cfg.high }},
            {{ cfg.open }},
            {{ cfg.close }},
        {% endfor %}
        {{agg_cols}}        
    from {{table_source}} ofdb 
    {% if granularity == "week" %}
        left join {{ source('silver_global', 'dim_calendar') }} as dc on ofdb.date_prices = dc.date
    {% endif %}
    )
    ,open_close as (
        select

        {{smaller_granularity_ref_col}},
        {{agg_cols}},

        {% for cfg in ohlc_configs %}
            {{ cfg.low }},
            {{ cfg.high }},
            first({{cfg.open}}) over(partition by {{parition_by_col}} order by {{smaller_granularity_ref_col}} asc ) as {{cfg.open}},
            first({{cfg.close}}) over(partition by {{parition_by_col}} order by {{smaller_granularity_ref_col}} desc) as {{cfg.close}},
        {% endfor %}

        ingest_date_time
        from join_calendar
    )
    ,agg as (
    select
        {{agg_cols}},

        {% for cfg in ohlc_configs %}
            min({{cfg.low}}) as {{ cfg.low }},
            max({{cfg.high}}) as {{ cfg.high }},
            max({{cfg.open}}) as {{ cfg.open }},
            max({{cfg.close}}) as {{ cfg.close }},
        {% endfor %}
        max(ingest_date_time) as ingest_date_time
        from open_close
    group by ALL
    )
    ,add_previous_price_change as (
        select *,
            {{ previous_price_change('close_usd', parition_by_col) }} AS change
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
