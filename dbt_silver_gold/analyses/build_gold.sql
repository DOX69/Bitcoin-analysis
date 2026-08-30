with base as (
    {{ create_update_agg(ref('obt_fact_day_btc'), 'week') }}
), counted as (
    select
        *,
        count(*) over (partition by iso_week_start_date) as row_count
    from base
)
select *
from counted
where row_count > 1
