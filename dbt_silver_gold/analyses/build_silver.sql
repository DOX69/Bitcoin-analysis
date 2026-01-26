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
select coalesce(chf.date,eur.date) as date_rates,
chf.rate as rate_usd_chf,
eur.rate as rate_usd_eur,
current_timestamp as update_date_time
from deduplicate_rate_chf as chf full join deduplicate_rate_eur as eur using (date)