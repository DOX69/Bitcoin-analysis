with calendar as (
    select generate_series(
        date '2009-12-31',
        current_date,
        interval '1 day'
    )::date as date
)
select
    date,
    date_trunc('week', date)::date as iso_week_start_date,
    date_trunc('month', date)::date as month_start_date,
    date_trunc('quarter', date)::date as quarter_start_date,
    date_trunc('year', date)::date as year_start_date
from calendar
