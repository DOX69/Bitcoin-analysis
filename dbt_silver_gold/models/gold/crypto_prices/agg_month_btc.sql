{{ 
    config(
        materialized='incremental',
        unique_key='month_start_date',
        on_schema_change='sync_all_columns'
        ) 
}}

{{ create_update_agg(ref("obt_fact_day_btc"), 'month')}}
