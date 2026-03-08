{%- macro create_update_agg(table_source, granularity) -%}
{% set period = 14 %}
{%- set currencies = ["usd", "chf", "eur"] -%}

{%- set ohlc_cols = ['low', 'high', 'open', 'close'] -%}
{%- set tech_cols = ['macd', 'macd_signal', 'macd_hist', 'sma_7', 'sma_50', 'sma_200', 'ema_7', 'ema_50', 'ema_200'] -%}
{%- set all_cols_to_agg = ohlc_cols + tech_cols -%}

{%- if granularity == "week" -%}
    {%- set smaller_granularity_ref_col = "date_prices" -%}
    {%- set agg_cols_str = "iso_week_start_date, month_start_date, quarter_start_date, year_start_date" -%}
    {%- set partition_by_col = "iso_week_start_date" -%}
    
{%- elif granularity == "month" %}
    {%- set smaller_granularity_ref_col = "iso_week_start_date" -%}
    {%- set agg_cols_str = "month_start_date, quarter_start_date, year_start_date" -%}
    {%- set partition_by_col = "month_start_date" -%}
    
{%- elif granularity == "quarter" %}
    {%- set smaller_granularity_ref_col = "month_start_date" -%}
    {%- set agg_cols_str = "quarter_start_date, year_start_date" -%}
    {%- set partition_by_col = "quarter_start_date" -%}
    
{%- elif granularity == "year" %}
    {%- set smaller_granularity_ref_col = "quarter_start_date" -%}
    {%- set agg_cols_str = "year_start_date" -%}
    {%- set partition_by_col = "year_start_date" -%}
{%- endif -%}

{%- set agg_cols = agg_cols_str.split(', ') -%}


With join_calendar as (
        select ingest_date_time,

        {{smaller_granularity_ref_col}},
        {% for cur in currencies -%}
            {% for col in all_cols_to_agg -%}
            {{ col }}_{{ cur }},
            {% endfor -%}
        {% endfor -%}
        {{ agg_cols_str }}
    from {{table_source}} ofdb 
    {% if granularity == "week" %}
        left join {{ source('silver_global', 'dim_calendar') }} as dc on ofdb.date_prices = dc.date
    {% endif %}
    )
    ,open_close as (
        select

        {{smaller_granularity_ref_col}},
        {{ agg_cols_str }},

        {% for cur in currencies -%}
            {% for col in all_cols_to_agg -%}
                {%- if col == 'low' -%}
                {{ col }}_{{ cur }},
                {%- elif col == 'high' -%}
                {{ col }}_{{ cur }},
                {%- elif col == 'open' -%}
                first({{ col }}_{{ cur }}) over(partition by {{partition_by_col}} order by {{smaller_granularity_ref_col}} asc ) as {{ col }}_{{ cur }},
                {%- else -%}
                {# for close and technical indicators, we take the last value of the period #}
                first({{ col }}_{{ cur }}) over(partition by {{partition_by_col}} order by {{smaller_granularity_ref_col}} desc) as {{ col }}_{{ cur }},
                {%- endif -%}
            {% endfor -%}
        {% endfor -%}

        ingest_date_time
        from join_calendar
    )
    ,agg as (
    select
        {{ partition_by_col }},
        {% for col in agg_cols -%}
            {%- if col != partition_by_col -%}
            min({{ col }}) as {{ col }},
            {%- endif -%}
        {%- endfor -%}

        {% for cur in currencies -%}
            {% for col in all_cols_to_agg -%}
                {%- if col == 'low' -%}
                min({{ col }}_{{ cur }}) as {{ col }}_{{ cur }},
                {%- elif col == 'high' -%}
                max({{ col }}_{{ cur }}) as {{ col }}_{{ cur }},
                {%- else -%}
                max({{ col }}_{{ cur }}) as {{ col }}_{{ cur }},
                {%- endif -%}
            {% endfor -%}
        {% endfor -%}
        max(ingest_date_time) as ingest_date_time
        from open_close
    group by {{ partition_by_col }}
    )
    ,add_previous_price_change as (
        select *,
            {{ previous_price_change('close_usd', partition_by_col) }} AS change
        from agg
    )
    ,add_rsi as (
        select *,
            {{ rsi('change', period, partition_by_col) }}
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
