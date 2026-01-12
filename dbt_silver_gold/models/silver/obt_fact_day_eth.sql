{{ 
    config(
        materialized='incremental'
        ) 
}}

with increment_data as (

        select date as date_prices,
            * except (date, time)
        from {{ source('bronze', 'eth_usd_ohlcv') }}

            {% if is_incremental() %}
        where ingest_date_time > (select max(ingest_date_time) from {{ this }})
            {% endif %}

    )
    , deduplicate_data as (
        select *, row_number() over (partition by date_prices order by ingest_date_time desc) as rn
        from increment_data
            qualify rn = 1
    )
select * except (rn),
    '{{ invocation_id }}' as dbt_batch_id
from deduplicate_data
