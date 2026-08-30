{% set period = 14 %}

with ranked as (
    select
        time,
        low,
        high,
        open,
        close,
        volume,
        date,
        ingest_date_time,
        row_number() over (partition by date order by ingest_date_time desc) as row_number
    from {{ source('bronze', 'btc_usd_ohlcv') }}
), deduplicated as (
    select time, low, high, open, close, volume, date, ingest_date_time
    from ranked
    where row_number = 1
), price_changes as (
    select
        *,
        {{ previous_price_change('close') }} as change
    from deduplicated
), get_rsi as (
    select
        *,
        {{ rsi('change', period) }}
    from price_changes
)
select
    time,
    low,
    high,
    open,
    close,
    volume,
    date,
    ingest_date_time,
    rsi,
    rsi_status
from get_rsi
order by date desc
