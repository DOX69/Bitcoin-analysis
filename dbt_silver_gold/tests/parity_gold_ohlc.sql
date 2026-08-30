with expected(model_name, period_start, low_usd, high_usd, open_usd, close_usd) as (
    values
        ('week', date '2024-01-01', 100::double precision, 130::double precision, 110::double precision, 125::double precision),
        ('week', date '2024-01-08', 120::double precision, 140::double precision, 125::double precision, 135::double precision),
        ('week', date '2024-01-29', 130::double precision, 150::double precision, 135::double precision, 145::double precision),
        ('week', date '2024-12-30', 180::double precision, 390::double precision, 250::double precision, 380::double precision),
        ('month', date '2024-01-01', 100::double precision, 140::double precision, 110::double precision, 135::double precision),
        ('month', date '2024-02-01', 130::double precision, 150::double precision, 135::double precision, 145::double precision),
        ('month', date '2024-12-01', 180::double precision, 280::double precision, 250::double precision, 210::double precision),
        ('month', date '2025-01-01', 290::double precision, 390::double precision, 310::double precision, 380::double precision),
        ('quarter', date '2024-01-01', 100::double precision, 150::double precision, 110::double precision, 145::double precision),
        ('quarter', date '2024-10-01', 180::double precision, 280::double precision, 250::double precision, 210::double precision),
        ('quarter', date '2025-01-01', 290::double precision, 390::double precision, 310::double precision, 380::double precision),
        ('year', date '2024-01-01', 100::double precision, 280::double precision, 110::double precision, 210::double precision),
        ('year', date '2025-01-01', 290::double precision, 390::double precision, 310::double precision, 380::double precision)
), actual as (
    select 'week', iso_week_start_date, low_usd, high_usd, open_usd, close_usd from {{ ref('agg_week_btc') }}
    union all
    select 'month', month_start_date, low_usd, high_usd, open_usd, close_usd from {{ ref('agg_month_btc') }}
    union all
    select 'quarter', quarter_start_date, low_usd, high_usd, open_usd, close_usd from {{ ref('agg_quarter_btc') }}
    union all
    select 'year', year_start_date, low_usd, high_usd, open_usd, close_usd from {{ ref('agg_year_btc') }}
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
