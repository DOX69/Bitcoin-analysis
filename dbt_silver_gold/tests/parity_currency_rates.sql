with expected(date_rates, rate_usd_chf, rate_usd_eur) as (
    values
        (date '2024-01-01', 0.90::double precision, 0.95::double precision),
        (date '2024-01-02', 0.90::double precision, 0.96::double precision),
        (date '2024-01-03', 0.92::double precision, 0.96::double precision)
), actual as (
    select date_rates, rate_usd_chf, rate_usd_eur
    from {{ ref('usd_to_other') }}
    where date_rates between date '2024-01-01' and date '2024-01-03'
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
