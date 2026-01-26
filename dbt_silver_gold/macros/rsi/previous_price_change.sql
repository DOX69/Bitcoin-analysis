{%- macro previous_price_change(column, date_column='date') -%}
    {{ column }} - LAG({{ column }}) OVER (ORDER BY {{ date_column }})
{%- endmacro -%}
