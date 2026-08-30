{{ config(tags=['fixture']) }}

with expected(
    date_prices, low_usd, high_usd, open_usd, close_usd, volume,
    macd_usd, rate_usd_chf, rate_usd_eur, low_chf, close_eur
) as (
    values
        (date '2024-01-01', 100::double precision, 120::double precision, 110::double precision, 115::double precision, 10::double precision, 10::double precision, 0.90::double precision, 0.95::double precision, 90::double precision, 109.25::double precision),
        (date '2024-01-02', 110::double precision, 130::double precision, 115::double precision, 125::double precision, 11::double precision, null::double precision, 0.90::double precision, 0.96::double precision, 99::double precision, 120::double precision),
        (date '2024-01-08', 120::double precision, 140::double precision, 125::double precision, 135::double precision, 12::double precision, 20::double precision, 0.92::double precision, 0.96::double precision, 110.40::double precision, 129.60::double precision),
        (date '2024-02-01', 130::double precision, 150::double precision, 135::double precision, 145::double precision, 13::double precision, 30::double precision, 0.95::double precision, 0.98::double precision, 123.50::double precision, 142.10::double precision),
        (date '2024-12-30', 200::double precision, 260::double precision, 250::double precision, 240::double precision, 14::double precision, null::double precision, 0.95::double precision, 0.98::double precision, 190::double precision, 235.20::double precision),
        (date '2024-12-31', 180::double precision, 280::double precision, 240::double precision, 210::double precision, 15::double precision, null::double precision, 0.95::double precision, 0.98::double precision, 171::double precision, 205.80::double precision),
        (date '2025-01-01', 300::double precision, 360::double precision, 310::double precision, 350::double precision, 16::double precision, null::double precision, 0.95::double precision, 0.98::double precision, 285::double precision, 343::double precision),
        (date '2025-01-05', 290::double precision, 390::double precision, 350::double precision, 380::double precision, 17::double precision, null::double precision, 0.95::double precision, 0.98::double precision, 275.50::double precision, 372.40::double precision)
), actual as (
    select
        date_prices, low_usd, high_usd, open_usd, close_usd, volume,
        macd_usd, rate_usd_chf, rate_usd_eur, low_chf, close_eur
    from {{ ref('obt_fact_day_btc') }}
)
select 'missing_or_changed' as failure, expected.*
from expected
except
select 'missing_or_changed', actual.*
from actual
union all
select 'unexpected' as failure, actual.*
from actual
except
select 'unexpected', expected.*
from expected
