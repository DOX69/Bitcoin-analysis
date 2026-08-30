{% set ohlc = ['low', 'high', 'open', 'close'] %}
{% set technical = ['macd', 'macd_signal', 'macd_hist', 'sma_7', 'sma_50', 'sma_200', 'ema_7', 'ema_50', 'ema_200'] %}
{% set currencies = ['usd', 'chf', 'eur'] %}
{% set gold_models = [
    ('agg_week_btc', ['iso_week_start_date', 'month_start_date', 'quarter_start_date', 'year_start_date']),
    ('agg_month_btc', ['month_start_date', 'quarter_start_date', 'year_start_date']),
    ('agg_quarter_btc', ['quarter_start_date', 'year_start_date']),
    ('agg_year_btc', ['year_start_date'])
] %}

with expected(model_name, column_name, data_type) as (
    values
        ('usd_to_other', 'date_rates', 'date'),
        ('usd_to_other', 'rate_usd_chf', 'double precision'),
        ('usd_to_other', 'rate_usd_eur', 'double precision'),
        ('usd_to_other', 'update_date_time', 'timestamp without time zone'),
        ('usd_to_other', 'dbt_batch_id', 'text'),
        ('fact_btc', 'date_indicators', 'date'),
        {% for column in technical %}
        ('fact_btc', '{{ column }}', 'double precision'),
        {% endfor %}
        ('fact_btc', 'ingest_date_time', 'timestamp without time zone'),
        ('fact_btc', 'dbt_batch_id', 'text'),
        ('obt_fact_day_btc', 'date_prices', 'date'),
        {% for column in ohlc + technical %}
        ('obt_fact_day_btc', '{{ column }}_usd', 'double precision'),
        {% endfor %}
        ('obt_fact_day_btc', 'volume', 'double precision'),
        ('obt_fact_day_btc', 'rsi', 'double precision'),
        ('obt_fact_day_btc', 'rsi_status', 'text'),
        ('obt_fact_day_btc', 'rate_usd_chf', 'double precision'),
        ('obt_fact_day_btc', 'rate_usd_eur', 'double precision'),
        {% for currency in ['chf', 'eur'] %}
            {% for column in ohlc + technical %}
        ('obt_fact_day_btc', '{{ column }}_{{ currency }}', 'double precision'),
            {% endfor %}
        {% endfor %}
        ('obt_fact_day_btc', 'ingest_date_time', 'timestamp without time zone'),
        ('obt_fact_day_btc', 'dbt_batch_id', 'text'),
        ('obt_fact_day_eth', 'date_prices', 'date'),
        {% for column in ohlc %}
        ('obt_fact_day_eth', '{{ column }}_usd', 'double precision'),
        {% endfor %}
        ('obt_fact_day_eth', 'volume', 'double precision'),
        ('obt_fact_day_eth', 'rsi', 'double precision'),
        ('obt_fact_day_eth', 'rsi_status', 'text'),
        ('obt_fact_day_eth', 'rate_usd_chf', 'double precision'),
        ('obt_fact_day_eth', 'rate_usd_eur', 'double precision'),
        {% for currency in ['chf', 'eur'] %}
            {% for column in ohlc %}
        ('obt_fact_day_eth', '{{ column }}_{{ currency }}', 'double precision'),
            {% endfor %}
        {% endfor %}
        ('obt_fact_day_eth', 'ingest_date_time', 'timestamp without time zone'),
        ('obt_fact_day_eth', 'dbt_batch_id', 'text'),
        {% for model_name, date_columns in gold_models %}
            {% for column in date_columns %}
        ('{{ model_name }}', '{{ column }}', 'date'),
            {% endfor %}
            {% for currency in currencies %}
                {% for column in ohlc + technical %}
        ('{{ model_name }}', '{{ column }}_{{ currency }}', 'double precision'),
                {% endfor %}
            {% endfor %}
        ('{{ model_name }}', 'rsi', 'double precision'),
        ('{{ model_name }}', 'rsi_status', 'text'),
        ('{{ model_name }}', 'ingest_date_time', 'timestamp without time zone'),
        ('{{ model_name }}', 'dbt_batch_id', 'text'){{ ',' if not loop.last else '' }}
        {% endfor %}
), model_relations(model_name, schema_name) as (
    values
        ('usd_to_other', '{{ ref("usd_to_other").schema }}'),
        ('fact_btc', '{{ ref("fact_btc").schema }}'),
        ('obt_fact_day_btc', '{{ ref("obt_fact_day_btc").schema }}'),
        ('obt_fact_day_eth', '{{ ref("obt_fact_day_eth").schema }}'),
        ('agg_week_btc', '{{ ref("agg_week_btc").schema }}'),
        ('agg_month_btc', '{{ ref("agg_month_btc").schema }}'),
        ('agg_quarter_btc', '{{ ref("agg_quarter_btc").schema }}'),
        ('agg_year_btc', '{{ ref("agg_year_btc").schema }}')
), actual as (
    select columns.table_name as model_name, columns.column_name, columns.data_type
    from information_schema.columns as columns
    inner join model_relations
        on model_relations.model_name = columns.table_name
        and model_relations.schema_name = columns.table_schema
)
select 'missing_or_changed' as failure, expected.*
from expected
except
select 'missing_or_changed', actual.*
from actual
union all
select 'unexpected' as failure, actual.*
from actual
except
select 'unexpected', expected.*
from expected
