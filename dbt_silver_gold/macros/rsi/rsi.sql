{%- macro rsi(column_change, period, date_column='date') -%}
{%- set average_gain -%}
avg(case when {{ column_change }} > 0 then {{ column_change }} else 0 end) over (
    order by {{ date_column }} rows between {{ period - 1 }} preceding and current row
)
{%- endset -%}
{%- set average_loss -%}
avg(case when {{ column_change }} < 0 then -{{ column_change }} else 0 end) over (
    order by {{ date_column }} rows between {{ period - 1 }} preceding and current row
)
{%- endset -%}
{%- set rsi_value -%}
round((100 - (100 / (1 + ({{ average_gain }}) / nullif(({{ average_loss }}), 0))))::numeric, 2)::double precision
{%- endset -%}
{{ average_gain }} as avg_gain,
{{ average_loss }} as avg_loss,
{{ rsi_value }} as rsi_calculated,
case when {{ rsi_value }} between 0 and 100 then {{ rsi_value }} else null end as rsi,
case
    when {{ rsi_value }} < 30 then 'oversold'
    when {{ rsi_value }} > 70 then 'overbought'
    else 'neutral'
end as rsi_status
{%- endmacro -%}
