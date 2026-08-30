{% macro create_update_agg(table_source, granularity) %}
{% set period = 14 %}
{% set currencies = ['usd', 'chf', 'eur'] %}
{% set ohlc_columns = ['low', 'high', 'open', 'close'] %}
{% set technical_columns = ['macd', 'macd_signal', 'macd_hist', 'sma_7', 'sma_50', 'sma_200', 'ema_7', 'ema_50', 'ema_200'] %}
{% set aggregate_columns = ohlc_columns + technical_columns %}

{% if granularity == 'week' %}
    {% set partition_column = 'iso_week_start_date' %}
    {% set date_columns = ['iso_week_start_date', 'month_start_date', 'quarter_start_date', 'year_start_date'] %}
{% elif granularity == 'month' %}
    {% set partition_column = 'month_start_date' %}
    {% set date_columns = ['month_start_date', 'quarter_start_date', 'year_start_date'] %}
{% elif granularity == 'quarter' %}
    {% set partition_column = 'quarter_start_date' %}
    {% set date_columns = ['quarter_start_date', 'year_start_date'] %}
{% elif granularity == 'year' %}
    {% set partition_column = 'year_start_date' %}
    {% set date_columns = ['year_start_date'] %}
{% else %}
    {{ exceptions.raise_compiler_error('Unsupported granularity: ' ~ granularity) }}
{% endif %}

with join_calendar as (
    select
        source.ingest_date_time,
        source.date_prices,
        {% for currency in currencies %}
            {% for column in aggregate_columns %}
        source.{{ column }}_{{ currency }},
            {% endfor %}
        {% endfor %}
        {% for column in date_columns %}
        calendar.{{ column }}{{ ',' if not loop.last else '' }}
        {% endfor %}
    from {{ table_source }} as source
    left join {{ ref('dim_calendar') }} as calendar
        on source.date_prices = calendar.date
), aggregated as (
    select
        {{ partition_column }},
        {% for column in date_columns %}
            {% if column != partition_column %}
        min({{ column }}) as {{ column }},
            {% endif %}
        {% endfor %}
        {% for currency in currencies %}
            {% for column in aggregate_columns %}
                {% if column == 'low' %}
        min({{ column }}_{{ currency }})::double precision as {{ column }}_{{ currency }},
                {% elif column == 'high' %}
        max({{ column }}_{{ currency }})::double precision as {{ column }}_{{ currency }},
                {% elif column == 'open' %}
        (array_agg({{ column }}_{{ currency }} order by date_prices asc))[1]::double precision as {{ column }}_{{ currency }},
                {% else %}
        (array_agg({{ column }}_{{ currency }} order by date_prices desc))[1]::double precision as {{ column }}_{{ currency }},
                {% endif %}
            {% endfor %}
        {% endfor %}
        max(ingest_date_time) as source_ingest_date_time
    from join_calendar
    group by {{ partition_column }}
), add_previous_price_change as (
    select
        *,
        {{ previous_price_change('close_usd', partition_column) }} as change
    from aggregated
), add_rsi as (
    select
        *,
        {{ rsi('change', period, partition_column) }}
    from add_previous_price_change
), increment_filter as (
    select *
    from add_rsi
    {% if is_incremental() %}
    where source_ingest_date_time > (select max(ingest_date_time) from {{ this }})
    {% endif %}
)
select
    {% for column in date_columns %}
    {{ column }},
    {% endfor %}
    {% for currency in currencies %}
        {% for column in aggregate_columns %}
    {{ column }}_{{ currency }},
        {% endfor %}
    {% endfor %}
    rsi::double precision as rsi,
    rsi_status,
    current_timestamp::timestamp without time zone as ingest_date_time,
    '{{ invocation_id }}' as dbt_batch_id
from increment_filter
{% endmacro %}
