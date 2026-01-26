{% macro last_value_not_null(column_name,order_by_column_name) %}
  coalesce({{column_name}}, last_value({{column_name}}, true) over (order by {{order_by_column_name}})) as {{column_name}}
{% endmacro %}