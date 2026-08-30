import { cache } from 'react';
import { executeQuery } from './postgres';
import {
    AggregatedDataListSchema,
    BitcoinHistorySchema,
    BitcoinMetricsSchema,
} from './schemas';

export type Currency = 'USD' | 'CHF' | 'EUR';
type CurrencyColumnSuffix = 'usd' | 'chf' | 'eur';

const CURRENCY_COLUMN_SUFFIXES = new Map<Currency, CurrencyColumnSuffix>([
    ['USD', 'usd'],
    ['CHF', 'chf'],
    ['EUR', 'eur'],
]);

const TABLES = {
    daily: 'dlh_silver__crypto_prices.obt_fact_day_btc',
    monthly: 'dlh_gold__crypto_prices.agg_month_btc',
    rates: 'dlh_silver__currency_rate.usd_to_other',
} as const;

const AGGREGATIONS = {
    weekly: {
        table: 'dlh_gold__crypto_prices.agg_week_btc',
        dateColumn: 'iso_week_start_date',
        dateTrunc: 'week',
    },
    monthly: {
        table: 'dlh_gold__crypto_prices.agg_month_btc',
        dateColumn: 'month_start_date',
        dateTrunc: 'month',
    },
    quarterly: {
        table: 'dlh_gold__crypto_prices.agg_quarter_btc',
        dateColumn: 'quarter_start_date',
        dateTrunc: 'quarter',
    },
} as const;

type CurrencyRates = { USD_CHF: number; USD_EUR: number };
const MONTHLY_HISTORY_THRESHOLD_DAYS = 1800;
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;

export const getCurrencyRates = cache(async (): Promise<CurrencyRates> => {
    try {
        const results = await executeQuery<{ rate_usd_chf: unknown; rate_usd_eur: unknown }>(`
            SELECT rate_usd_chf, rate_usd_eur
            FROM ${TABLES.rates}
            ORDER BY date_rates DESC
            LIMIT 1
        `);

        if (results.length === 0) {
            throw new Error('No currency rates available');
        }

        return {
            USD_CHF: Number(results[0].rate_usd_chf),
            USD_EUR: Number(results[0].rate_usd_eur),
        };
    } catch (error) {
        console.error('DB_ERROR: Failed to fetch currency rates:', error);
        throw error;
    }
});

export const convertPrice = (
    usdPrice: number,
    currency: Currency,
    rates: CurrencyRates
): number => {
    if (currency === 'CHF') return usdPrice * rates.USD_CHF;
    if (currency === 'EUR') return usdPrice * rates.USD_EUR;
    return usdPrice;
};

export const getCurrentBitcoinMetrics = cache(async (currency: Currency = 'USD') => {
    try {
        const ratesPromise = currency === 'USD' ? Promise.resolve(null) : getCurrencyRates();
        const [results, rates] = await Promise.all([
            executeQuery<{
                current_price: unknown;
                high_24h: unknown;
                low_24h: unknown;
                volume_24h: unknown;
                rsi: unknown;
            }>(`
                SELECT
                    close_usd AS current_price,
                    high_usd AS high_24h,
                    low_usd AS low_24h,
                    volume AS volume_24h,
                    rsi
                FROM ${TABLES.daily}
                ORDER BY date_prices DESC
                LIMIT 2
            `),
            ratesPromise,
        ]);

        if (results.length < 2) {
            throw new Error('Insufficient data to calculate metrics');
        }

        const convert = (value: unknown) => {
            const price = Number(value);
            return rates ? convertPrice(price, currency, rates) : price;
        };
        const currentPrice = convert(results[0].current_price);
        const previousPrice = convert(results[1].current_price);
        const change24h = currentPrice - previousPrice;

        return BitcoinMetricsSchema.parse({
            currentPrice,
            change24h,
            changePercent24h: (change24h / previousPrice) * 100,
            volume24h: Number(results[0].volume_24h),
            high24h: convert(results[0].high_24h),
            low24h: convert(results[0].low_24h),
            rsi: results[0].rsi == null ? undefined : Number(results[0].rsi),
        });
    } catch (error) {
        console.error('DB_ERROR: Failed to fetch Bitcoin metrics:', error);
        throw error;
    }
});

function getDateFilter(
    dateColumn: 'date_prices' | 'month_start_date',
    days: number,
    startDate?: string,
    endDate?: string
): { clause: string; parameters: unknown[] } {
    if (startDate && endDate) {
        const monthRange = dateColumn === 'month_start_date'
            ? `date_trunc('month', $1::date)::date AND date_trunc('month', $2::date)::date`
            : '$1::date AND $2::date';
        return {
            clause: `${dateColumn} BETWEEN ${monthRange}`,
            parameters: [startDate, endDate],
        };
    }

    return {
        clause: `${dateColumn} >= CURRENT_DATE - $1::integer`,
        parameters: [days],
    };
}

function getCustomRangeDays(startDate?: string, endDate?: string): number | undefined {
    if (!startDate || !endDate) return undefined;

    const start = Date.parse(`${startDate}T00:00:00.000Z`);
    const end = Date.parse(`${endDate}T00:00:00.000Z`);
    if (Number.isNaN(start) || Number.isNaN(end)) return undefined;

    return Math.floor((end - start) / MILLISECONDS_PER_DAY) + 1;
}

export const getHistoricalPrices = cache(async (
    days: number = 30,
    startDate?: string,
    endDate?: string,
    currency: Currency = 'USD'
) => {
    try {
        const effectiveDays = getCustomRangeDays(startDate, endDate) ?? days;
        const useMonthlyAggregation = effectiveDays >= MONTHLY_HISTORY_THRESHOLD_DAYS;
        const dateColumn = useMonthlyAggregation ? 'month_start_date' : 'date_prices';
        const { clause, parameters } = getDateFilter(dateColumn, days, startDate, endDate);
        const table = useMonthlyAggregation ? TABLES.monthly : TABLES.daily;
        const volume = useMonthlyAggregation ? '0 AS volume' : 'volume';
        const currencySuffix = CURRENCY_COLUMN_SUFFIXES.get(currency) ?? 'usd';
        const rsiStatus = useMonthlyAggregation
            ? `CASE
                    WHEN rsi > 70 THEN 'Overbought'
                    WHEN rsi < 30 THEN 'Oversold'
                    ELSE 'Neutral'
               END AS rsi_status`
            : 'rsi_status';

        const results = await executeQuery<Record<string, unknown>>(`
            SELECT
                ${dateColumn} AS date,
                open_${currencySuffix} AS open,
                high_${currencySuffix} AS high,
                low_${currencySuffix} AS low,
                close_${currencySuffix} AS close,
                ${volume},
                rsi,
                ${rsiStatus},
                macd_${currencySuffix} AS macd,
                macd_signal_${currencySuffix} AS macd_signal,
                macd_hist_${currencySuffix} AS macd_hist,
                sma_7_${currencySuffix} AS sma_7,
                sma_50_${currencySuffix} AS sma_50,
                sma_200_${currencySuffix} AS sma_200,
                ema_7_${currencySuffix} AS ema_7,
                ema_50_${currencySuffix} AS ema_50,
                ema_200_${currencySuffix} AS ema_200
            FROM ${table}
            WHERE ${clause}
            ORDER BY ${dateColumn} ASC
        `, parameters);

        return BitcoinHistorySchema.parse(results);
    } catch (error) {
        console.error('Failed to fetch historical prices:', error);
        throw error;
    }
});

export const getAggregatedData = cache(async (
    aggregation: keyof typeof AGGREGATIONS = 'weekly'
) => {
    try {
        const { table, dateColumn, dateTrunc } = AGGREGATIONS[aggregation];
        const results = await executeQuery<Record<string, unknown>>(`
            SELECT
                aggregated.${dateColumn} AS period,
                AVG(daily.close_usd) AS "avgPrice",
                aggregated.high_usd AS "maxPrice",
                aggregated.low_usd AS "minPrice",
                COALESCE(SUM(daily.volume), 0) AS "totalVolume"
            FROM ${table} AS aggregated
            LEFT JOIN ${TABLES.daily} AS daily
                ON date_trunc('${dateTrunc}', daily.date_prices)::date = aggregated.${dateColumn}
            GROUP BY aggregated.${dateColumn}, aggregated.high_usd, aggregated.low_usd
            ORDER BY aggregated.${dateColumn} DESC
            LIMIT 12
        `);

        return AggregatedDataListSchema.parse(results);
    } catch (error) {
        console.error('DB_ERROR: Failed to fetch aggregated data:', error);
        throw error;
    }
});
