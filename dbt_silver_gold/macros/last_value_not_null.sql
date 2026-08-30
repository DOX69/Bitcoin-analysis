{% macro last_value_not_null(column_name,order_by_column_name) %}
  (array_agg({{ column_name }}) filter (where {{ column_name }} is not null) over (
    order by {{ order_by_column_name }} rows between unbounded preceding and current row
  ))[count({{ column_name }}) over (
    order by {{ order_by_column_name }} rows between unbounded preceding and current row
  )::integer] as {{ column_name }}
{% endmacro %}
