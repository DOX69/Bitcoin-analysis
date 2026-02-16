{% macro check_ema_continuity() %}
  {% set query %}
    select count(*) as row_count from {{ ref('obt_fact_day_btc') }}
  {% endset %}

  {% set results = run_query(query) %}
  
  {% if execute %}
    {{ log(" Row Count Check ", info=True) }}
    {% do results.print_table() %}
  {% endif %}
{% endmacro %}
