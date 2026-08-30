{{
    config(
        materialized='incremental',
        unique_key='date_rates',
        on_schema_change='sync_all_columns'
    )
}}

with ranked_eur as (
    select
        date,
        rate,
        ingest_date_time,
        row_number() over (partition by date order by ingest_date_time desc) as row_number
    from {{ source('bronze', 'usd_eur_rates') }}
), deduplicated_eur as (
    select date, rate, ingest_date_time
    from ranked_eur
    where row_number = 1
), ranked_chf as (
    select
        date,
        rate,
        ingest_date_time,
        row_number() over (partition by date order by ingest_date_time desc) as row_number
    from {{ source('bronze', 'usd_chf_rates') }}
), deduplicated_chf as (
    select date, rate, ingest_date_time
    from ranked_chf
    where row_number = 1
), full_join_rates as (
    select
        coalesce(chf.date, eur.date) as date_rates,
        chf.rate as rate_usd_chf,
        eur.rate as rate_usd_eur,
        least(chf.ingest_date_time, eur.ingest_date_time) as ingest_date_time
    from deduplicated_chf as chf
    full join deduplicated_eur as eur using (date)
), all_dates_rates as (
    select
        calendar.date as date_rates,
        {{ last_value_not_null('rate_usd_chf', 'calendar.date') }},
        {{ last_value_not_null('rate_usd_eur', 'calendar.date') }},
        {{ last_value_not_null('ingest_date_time', 'calendar.date') }}
    from {{ ref('dim_calendar') }} as calendar
    left join full_join_rates
        on calendar.date = full_join_rates.date_rates
), increment_data as (
    select
        date_rates,
        rate_usd_chf::double precision as rate_usd_chf,
        rate_usd_eur::double precision as rate_usd_eur,
        current_timestamp::timestamp without time zone as update_date_time,
        '{{ invocation_id }}' as dbt_batch_id
    from all_dates_rates
    where rate_usd_chf is not null
      and rate_usd_eur is not null
    {% if is_incremental() %}
      and (
          date_rates > coalesce((select max(date_rates) from {{ this }}), date '1900-01-01')
          or date_rates >= current_date - interval '10 days'
          or ingest_date_time > (select max(update_date_time) from {{ this }})
      )
    {% endif %}
)
select *
from increment_data
