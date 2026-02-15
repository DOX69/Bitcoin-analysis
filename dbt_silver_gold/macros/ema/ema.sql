{%- macro ema(source_cte, close_column='close', date_column='date') -%}
{#
    Computes EMA-9, EMA-21, EMA-55, EMA-100, EMA-150, EMA-200 using a recursive CTE.
    
    Args:
        source_cte: Name of the CTE/ref containing the price data
        close_column: Column name for the closing price
        date_column: Column name for the date/ordering column
    
    Returns columns: ema_9, ema_21, ema_55, ema_100, ema_150, ema_200
    
    Formula: EMA[n] = α × Close[n] + (1 − α) × EMA[n−1]
    Alpha:   α = 2 / (period + 1)
#}

{% set alpha_9   = 2.0 / (9 + 1) %}
{% set alpha_21  = 2.0 / (21 + 1) %}
{% set alpha_55  = 2.0 / (55 + 1) %}
{% set alpha_100 = 2.0 / (100 + 1) %}
{% set alpha_150 = 2.0 / (150 + 1) %}
{% set alpha_200 = 2.0 / (200 + 1) %}

ema_numbered as (
    select
        *,
        row_number() over (order by {{ date_column }}) as _ema_rn
    from {{ source_cte }}
),
ema_recursive as (
    -- Anchor: seed with first close price
    select
        *,
        cast({{ close_column }} as double) as ema_9,
        cast({{ close_column }} as double) as ema_21,
        cast({{ close_column }} as double) as ema_55,
        cast({{ close_column }} as double) as ema_100,
        cast({{ close_column }} as double) as ema_150,
        cast({{ close_column }} as double) as ema_200
    from ema_numbered
    where _ema_rn = 1

    union all

    -- Recursive step
    select
        n.*,
        round({{ alpha_9 }}   * n.{{ close_column }} + (1 - {{ alpha_9 }})   * e.ema_9, 2) as ema_9,
        round({{ alpha_21 }}  * n.{{ close_column }} + (1 - {{ alpha_21 }})  * e.ema_21, 2) as ema_21,
        round({{ alpha_55 }}  * n.{{ close_column }} + (1 - {{ alpha_55 }})  * e.ema_55, 2) as ema_55,
        round({{ alpha_100 }} * n.{{ close_column }} + (1 - {{ alpha_100 }}) * e.ema_100, 2) as ema_100,
        round({{ alpha_150 }} * n.{{ close_column }} + (1 - {{ alpha_150 }}) * e.ema_150, 2) as ema_150,
        round({{ alpha_200 }} * n.{{ close_column }} + (1 - {{ alpha_200 }}) * e.ema_200, 2) as ema_200
    from ema_numbered n
    inner join ema_recursive e on n._ema_rn = e._ema_rn + 1
)
{%- endmacro -%}
