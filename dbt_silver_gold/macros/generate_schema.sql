{% macro generate_schema_name(custom_schema_name, node) %}
    {# 
      custom_schema_name: schema defined in the model config (if any)
      node: contains metadata about the model, including its file path
    #}

    {# Get the folder path relative to the models directory #}
    {% set replace_slash = node.path | replace('/', '|') | replace('\\', '|') %}
    {% set splited_path_array = replace_slash.split('|') %}
    {% set model_full_path = splited_path_array[:-1] | join('__') %}
    {# {% set model_full_path = node.path | replace('models/', '') | replace('.sql', '') | replace('/', '__') | replace('\\', '__') %} #}

    {# Use target.schema as base schema prefix #}
    {% set base_schema = 'dlh_' ~ model_full_path %}
    {# If a custom schema is defined in the model, append it #}
    {% if custom_schema_name is not none %}
        {% set schema_name = base_schema ~ '_' ~ custom_schema_name %}
    {% else %}
        {% set schema_name = base_schema %}
    {% endif %}

    {{ schema_name | lower }}
{% endmacro %}