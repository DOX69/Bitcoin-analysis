{{ 
    config(
        materialized='incremental',
        unique_key='year_start_date',
        on_schema_change='sync_all_columns'
        ) 
}}

{{ create_update_agg(ref("agg_week_btc"), 'year')}}