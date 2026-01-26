with base as (
    {{ create_update_agg(ref("obt_fact_day_btc"), 'week')}}
)
select *, count(*) over(partition by 
iso_week_start_date) ct from base
qualify ct > 1