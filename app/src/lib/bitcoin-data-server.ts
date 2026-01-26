
import { executeQuery } from './databricks';
import { cache } from 'react';
import { env } from './env';
import {
    BitcoinMetricsSchema,
    BitcoinHistorySchema,
    AggregatedDataListSchema
} from './schemas';

console.log('DATACENTER SERVER LOADED - ENV HOST:', env?.DATABRICKS_HOST ? 'SET' : 'UNSET');

/**
 * Get current Bitcoin price and 24h metrics
 * Cached per-request for deduplication
 */
export const getCurrentBitcoinMetrics = cache(async () => {
    try {
        const query = `
      SELECT
        close_usd as current_price,
        high_usd as high_24h,
        low_usd as low_24h,
        volume as volume_24h,
        rsi as rsi
      FROM prod.dlh_silver__crypto_prices.obt_fact_day_btc
      ORDER BY date_prices DESC
      LIMIT 2
    `;

        const results = await executeQuery<any>(query);

        if (results.length < 2) {
            throw new Error('Insufficient data to calculate metrics');
        }

        const latest = results[0];
        const previous = results[1];

        const change24h = latest.current_price - previous.current_price;
        const changePercent24h = (change24h / previous.current_price) * 100;

        const metrics = {
            currentPrice: latest.current_price,
            change24h,
            changePercent24h,
            volume24h: latest.volume_24h,
            high24h: latest.high_24h,
            low24h: latest.low_24h,
            rsi: latest.rsi || 50,
        };

        return BitcoinMetricsSchema.parse(metrics);
    } catch (error) {
        console.error('DB_ERROR: Failed to fetch Bitcoin metrics:', error);
        throw error;
    }
});

/**
 * Get historical Bitcoin prices for charting
 * Cached based on arguments
 */
export const getHistoricalPrices = cache(async (
    days: number = 30,
    startDate?: string,
    endDate?: string
) => {
    try {
        let whereClause = `date_prices >= DATEADD(day, -${days}, CURRENT_DATE())`;

        if (startDate && endDate) {
            whereClause = `date_prices BETWEEN '${startDate}' AND '${endDate}'`;
        }

        const query = `
      SELECT
        date_prices as date,
        open_usd as open,
        high_usd as high,
        low_usd as low,
        close_usd as close,
        volume,
        rsi,
        rsi_status
      FROM prod.dlh_silver__crypto_prices.obt_fact_day_btc
      WHERE ${whereClause}
      ORDER BY date_prices ASC
    `;

        const results = await executeQuery<any>(query);
        return BitcoinHistorySchema.parse(results);
    } catch (error) {
        console.error('Failed to fetch historical prices:', error);
        throw error;
    }
});

/**
 * Get aggregated data (weekly, monthly, etc.)
 */
export const getAggregatedData = cache(async (
    aggregation: 'weekly' | 'monthly' | 'quarterly' = 'weekly'
) => {
    try {
        const tableSuffix = aggregation === 'weekly' ? 'week'
            : aggregation === 'monthly' ? 'month'
                : aggregation === 'quarterly' ? 'quarter'
                    : 'week';

        const tableName = `prod.dlh_gold__crypto_prices.agg_${tableSuffix}_btc`;
        const dateCol = aggregation === 'weekly' ? 'iso_week_start_date'
            : aggregation === 'monthly' ? 'month_start_date'
                : aggregation === 'quarterly' ? 'quarter_start_date'
                    : 'iso_week_start_date';

        const query = `
      SELECT
        ${dateCol} as period,
        close_usd as avgPrice,
        high_usd as maxPrice,
        low_usd as minPrice,
        0 as totalVolume
      FROM ${tableName}
      ORDER BY ${dateCol} DESC
      LIMIT 12
    `;

        const results = await executeQuery<any>(query);
        return AggregatedDataListSchema.parse(results);
    } catch (error) {
        console.error('DB_ERROR: Failed to fetch aggregated data:', error);
        throw error;
    }
});
