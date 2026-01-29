{% test percentage_range(model, column_name) %}
    select *
    from {{ model }}
    where {{ column_name }} < 0 or {{ column_name }} > 100
{% endtest %}
