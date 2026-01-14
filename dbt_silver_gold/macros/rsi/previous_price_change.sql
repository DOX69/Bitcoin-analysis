{%- macro previous_price_change(column) -%}
    {{ column }} - LAG({{ column }}) OVER (ORDER BY date)
{%- endmacro -%}