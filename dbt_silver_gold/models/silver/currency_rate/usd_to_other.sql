{{ 
            config(
                materialized='incremental',
                unique_key='date_rates',
                on_schema_change='sync_all_columns'
                ) 
        }}

{%set source_schema_name = 'bronze' %}

WITH deduplicate_rate_eur as (
select *, row_number() over (partition by date order by ingest_date_time desc) as rn
from {{ source(source_schema_name, 'usd_eur_rates') }}
    qualify rn = 1
)
, deduplicate_rate_chf as (
select *, row_number() over (partition by date order by ingest_date_time desc) as rn
from {{ source(source_schema_name, 'usd_chf_rates') }}
    qualify rn = 1
)
, calendar as (
    select distinct date
    from {{ source('silver_global', 'dim_calendar') }}
    where date >= '2009-12-31' and date <= current_date
)
, full_join_rates as (
 select coalesce(chf.date,eur.date) as date_rates,
chf.rate as rate_usd_chf,
eur.rate as rate_usd_eur,
least(chf.ingest_date_time,eur.ingest_date_time) as ingest_date_time
from deduplicate_rate_chf as chf full join deduplicate_rate_eur as eur using (date)
)
, all_dates_rates as (
select calendar.date as date_rates,
{{last_value_not_null('rate_usd_chf','calendar.date')}} ,
{{last_value_not_null('rate_usd_eur','calendar.date')}},
{{last_value_not_null('ingest_date_time','calendar.date')}}

from calendar left join full_join_rates on calendar.date = full_join_rates.date_rates
)
, increment_data as (
select date_rates,
cast(rate_usd_chf as double) as rate_usd_chf,
cast(rate_usd_eur as double) as rate_usd_eur,
current_timestamp as update_date_time,
'{{ invocation_id }}' as dbt_batch_id
from all_dates_rates

    {% if is_incremental() %}
where ingest_date_time > (select max(update_date_time) from {{ this }})
    {% endif %}
)
select * from increment_data