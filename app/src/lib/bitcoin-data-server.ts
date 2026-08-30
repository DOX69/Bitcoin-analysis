import { cache } from 'react';
import { executeQuery } from './postgres';
import {
    AggregatedDataListSchema,
    BitcoinHistorySchema,
    BitcoinMetricsSchema,
} from './schemas';

export type Currency = 'USD' | 'CHF' | 'EUR';

const TABLES = {
    daily: 'dlh_silver__crypto_prices.obt_fact_day_btc',
    monthly: 'dlh_gold__crypto_prices.agg_month_btc',
    rates: 'dlh_silver__currency_rate.usd_to_other',
} as const;

const AGGREGATIONS = {
    weekly: {
        table: 'dlh_gold__crypto_prices.agg_week_btc',
        dateColumn: 'iso_week_start_date',
    },
    monthly: {
        table: 'dlh_gold__crypto_prices.agg_month_btc',
        dateColumn: 'month_start_date',
    },
    quarterly: {
        table: 'dlh_gold__crypto_prices.agg_quarter_btc',
        dateColumn: 'quarter_start_date',
    },
} as const;

type CurrencyRates = { USD_CHF: number; USD_EUR: number };

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
            rsi: Number(results[0].rsi) || 50,
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
        return {
            clause: `${dateColumn} BETWEEN $1::date AND $2::date`,
            parameters: [startDate, endDate],
        };
    }

    return {
        clause: `${dateColumn} >= CURRENT_DATE - $1::integer`,
        parameters: [days],
    };
}

export const getHistoricalPrices = cache(async (
    days: number = 30,
    startDate?: string,
    endDate?: string,
    currency: Currency = 'USD'
) => {
    try {
        const useMonthlyAggregation = days >= 1800;
        const dateColumn = useMonthlyAggregation ? 'month_start_date' : 'date_prices';
        const { clause, parameters } = getDateFilter(dateColumn, days, startDate, endDate);
        const table = useMonthlyAggregation ? TABLES.monthly : TABLES.daily;
        const volume = useMonthlyAggregation ? '0 AS volume' : 'volume';
        const rsiStatus = useMonthlyAggregation
            ? `CASE
                    WHEN rsi > 70 THEN 'Overbought'
                    WHEN rsi < 30 THEN 'Oversold'
                    ELSE 'Neutral'
               END AS rsi_status`
            : 'rsi_status';

        const ratesPromise = currency === 'USD' ? Promise.resolve(null) : getCurrencyRates();
        const [results, rates] = await Promise.all([
            executeQuery<Record<string, unknown>>(`
                SELECT
                    ${dateColumn} AS date,
                    open_usd AS open,
                    high_usd AS high,
                    low_usd AS low,
                    close_usd AS close,
                    ${volume},
                    rsi,
                    ${rsiStatus},
                    macd_usd AS macd,
                    macd_signal_usd AS macd_signal,
                    macd_hist_usd AS macd_hist,
                    sma_7_usd AS sma_7,
                    sma_50_usd AS sma_50,
                    sma_200_usd AS sma_200,
                    ema_7_usd AS ema_7,
                    ema_50_usd AS ema_50,
                    ema_200_usd AS ema_200
                FROM ${table}
                WHERE ${clause}
                ORDER BY ${dateColumn} ASC
            `, parameters),
            ratesPromise,
        ]);

        if (!rates) {
            return BitcoinHistorySchema.parse(results);
        }

        const priceFields = [
            'open', 'high', 'low', 'close',
            'sma_7', 'sma_50', 'sma_200',
            'ema_7', 'ema_50', 'ema_200',
            'macd', 'macd_signal', 'macd_hist',
        ] as const;
        const convertedResults = results.map(row => {
            const converted = { ...row };
            for (const field of priceFields) {
                if (row[field] !== null && row[field] !== undefined) {
                    converted[field] = convertPrice(Number(row[field]), currency, rates);
                }
            }
            return converted;
        });

        return BitcoinHistorySchema.parse(convertedResults);
    } catch (error) {
        console.error('Failed to fetch historical prices:', error);
        throw error;
    }
});

export const getAggregatedData = cache(async (
    aggregation: keyof typeof AGGREGATIONS = 'weekly'
) => {
    try {
        const { table, dateColumn } = AGGREGATIONS[aggregation];
        const results = await executeQuery<Record<string, unknown>>(`
            SELECT
                ${dateColumn} AS period,
                close_usd AS "avgPrice",
                high_usd AS "maxPrice",
                low_usd AS "minPrice",
                0 AS "totalVolume"
            FROM ${table}
            ORDER BY ${dateColumn} DESC
            LIMIT 12
        `);

        return AggregatedDataListSchema.parse(results);
    } catch (error) {
        console.error('DB_ERROR: Failed to fetch aggregated data:', error);
        throw error;
    }
});
