{%- macro ema(source_cte, close_column='close', date_column='date', chunk_size=100, max_chunks=50, initial_ema_cte=none) -%}
{#
    Computes EMA using chunked recursive CTEs (for full history) or single recursion (for incremental).
    If initial_ema_cte is provided, it uses those values as a seed for the first row.
#}

{%- set alpha_9   = 2.0 / (9 + 1) -%}
{%- set alpha_21  = 2.0 / (21 + 1) -%}
{%- set alpha_55  = 2.0 / (55 + 1) -%}
{%- set alpha_100 = 2.0 / (100 + 1) -%}
{%- set alpha_150 = 2.0 / (150 + 1) -%}
{%- set alpha_200 = 2.0 / (200 + 1) -%}

ema_numbered as (
    select
        *,
        row_number() over (order by {{ date_column }}) as _ema_rn
    from {{ source_cte }}
)

{%- if initial_ema_cte is not none -%}

, ema_recursive as (
    -- Fast path: Single recursion seeded by existing values
    select
        n.*,
        cast(round({{ alpha_9 }}   * n.{{ close_column }} + (1 - {{ alpha_9 }})   * init.ema_9, 2) as double) as ema_9,
        cast(round({{ alpha_21 }}  * n.{{ close_column }} + (1 - {{ alpha_21 }})  * init.ema_21, 2) as double) as ema_21,
        cast(round({{ alpha_55 }}  * n.{{ close_column }} + (1 - {{ alpha_55 }})  * init.ema_55, 2) as double) as ema_55,
        cast(round({{ alpha_100 }} * n.{{ close_column }} + (1 - {{ alpha_100 }}) * init.ema_100, 2) as double) as ema_100,
        cast(round({{ alpha_150 }} * n.{{ close_column }} + (1 - {{ alpha_150 }}) * init.ema_150, 2) as double) as ema_150,
        cast(round({{ alpha_200 }} * n.{{ close_column }} + (1 - {{ alpha_200 }}) * init.ema_200, 2) as double) as ema_200
    from ema_numbered n
    cross join {{ initial_ema_cte }} init
    where n._ema_rn = 1

    union all

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

{%- else -%}

{%- for i in range(max_chunks) -%}
{%- set start_rn = i * chunk_size + 1 -%}
{%- set end_rn = (i + 1) * chunk_size -%}
{%- set prev_cte = 'ema_chunk_' ~ (i - 1) -%}
{%- set curr_cte = 'ema_chunk_' ~ i -%}

, {{ curr_cte }} as (
    -- Anchor
    select
        n.*,
        {%- if i == 0 %}
        -- First chunk: Seed with first close price
        cast({{ close_column }} as double) as ema_9,
        cast({{ close_column }} as double) as ema_21,
        cast({{ close_column }} as double) as ema_55,
        cast({{ close_column }} as double) as ema_100,
        cast({{ close_column }} as double) as ema_150,
        cast({{ close_column }} as double) as ema_200
        {%- else %}
        -- Subsequent chunks: Seed using last EMA from previous chunk
        cast(round({{ alpha_9 }}   * n.{{ close_column }} + (1 - {{ alpha_9 }})   * prev.ema_9, 2) as double) as ema_9,
        cast(round({{ alpha_21 }}  * n.{{ close_column }} + (1 - {{ alpha_21 }})  * prev.ema_21, 2) as double) as ema_21,
        cast(round({{ alpha_55 }}  * n.{{ close_column }} + (1 - {{ alpha_55 }})  * prev.ema_55, 2) as double) as ema_55,
        cast(round({{ alpha_100 }} * n.{{ close_column }} + (1 - {{ alpha_100 }}) * prev.ema_100, 2) as double) as ema_100,
        cast(round({{ alpha_150 }} * n.{{ close_column }} + (1 - {{ alpha_150 }}) * prev.ema_150, 2) as double) as ema_150,
        cast(round({{ alpha_200 }} * n.{{ close_column }} + (1 - {{ alpha_200 }}) * prev.ema_200, 2) as double) as ema_200
        {%- endif %}
    from ema_numbered n
    {%- if i > 0 %}
    cross join (select * from {{ prev_cte }} where _ema_rn = {{ start_rn - 1 }}) prev
    {%- endif %}
    where n._ema_rn = {{ start_rn }}

    union all

    -- Recursive Step
    select
        n.*,
        round({{ alpha_9 }}   * n.{{ close_column }} + (1 - {{ alpha_9 }})   * e.ema_9, 2) as ema_9,
        round({{ alpha_21 }}  * n.{{ close_column }} + (1 - {{ alpha_21 }})  * e.ema_21, 2) as ema_21,
        round({{ alpha_55 }}  * n.{{ close_column }} + (1 - {{ alpha_55 }})  * e.ema_55, 2) as ema_55,
        round({{ alpha_100 }} * n.{{ close_column }} + (1 - {{ alpha_100 }}) * e.ema_100, 2) as ema_100,
        round({{ alpha_150 }} * n.{{ close_column }} + (1 - {{ alpha_150 }}) * e.ema_150, 2) as ema_150,
        round({{ alpha_200 }} * n.{{ close_column }} + (1 - {{ alpha_200 }}) * e.ema_200, 2) as ema_200
    from ema_numbered n
    inner join {{ curr_cte }} e on n._ema_rn = e._ema_rn + 1
    where n._ema_rn <= {{ end_rn }}
)
{%- endfor -%}

, ema_recursive as (
    {%- for i in range(max_chunks) -%}
    select * from ema_chunk_{{ i }}
    {%- if not loop.last %} union all {% endif -%}
    {%- endfor -%}
)

{%- endif -%}
{%- endmacro -%}
