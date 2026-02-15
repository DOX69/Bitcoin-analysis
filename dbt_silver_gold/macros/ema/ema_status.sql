{%- macro ema_status(close_column='close', date_column='date') -%}
{#
    Derives EMA trend status and crossover signals from ema_9, ema_21, ema_55.
    Must be called AFTER the ema() macro has added ema_9, ema_21, ema_55 columns.
    
    Returns columns:
        ema_status: strong_uptrend | strong_downtrend | bullish_correction | bearish_correction | consolidation
        ema_signal: buy | sell | hold
#}

CASE
    WHEN ema_9 > ema_21 AND ema_21 > ema_55 THEN 'strong_uptrend'
    WHEN ema_9 < ema_21 AND ema_21 < ema_55 THEN 'strong_downtrend'
    WHEN ema_9 < ema_21 AND {{ close_column }} > ema_55 THEN 'bullish_correction'
    WHEN ema_9 > ema_21 AND {{ close_column }} < ema_55 THEN 'bearish_correction'
    ELSE 'consolidation'
END AS ema_status,

-- Crossover signal detection using LAG
CASE
    WHEN ema_9 > ema_21
         AND LAG(ema_9) OVER (ORDER BY {{ date_column }}) <= LAG(ema_21) OVER (ORDER BY {{ date_column }})
         AND ema_9 > ema_55
         AND ema_21 > ema_55
    THEN 'buy'
    WHEN ema_9 < ema_21
         AND LAG(ema_9) OVER (ORDER BY {{ date_column }}) >= LAG(ema_21) OVER (ORDER BY {{ date_column }})
         AND ema_9 < ema_55
         AND ema_21 < ema_55
    THEN 'sell'
    ELSE 'hold'
END AS ema_signal

{%- endmacro -%}
