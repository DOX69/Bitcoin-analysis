// Bitcoin data fetching API using Databricks
import { executeQuery, getDatabricksConfig } from './databricks';

export interface BitcoinPrice {
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

export interface BitcoinMetrics {
    currentPrice: number;
    change24h: number;
    changePercent24h: number;
    volume24h: number;
    high24h: number;
    low24h: number;
    rsi: number;
}

export interface AggregatedData {
    period: string;
    avgPrice: number;
    maxPrice: number;
    minPrice: number;
    totalVolume: number;
}

/**
 * Get current Bitcoin price and 24h metrics
 */
export async function getCurrentBitcoinMetrics(): Promise<BitcoinMetrics> {
    const config = getDatabricksConfig();

    try {
        // Query latest data from silver layer OBT
        const query = `
      SELECT 
        close as current_price,
        high as high_24h,
        low as low_24h,
        volume as volume_24h,
        rsi as rsi
      FROM prod.dlh_silver__crypto_prices.obt_fact_day_btc
      ORDER BY date_prices DESC
      LIMIT 2
    `;

        const results = await executeQuery<any>(query, config);

        if (results.length < 2) {
            throw new Error('Insufficient data to calculate metrics');
        }

        const latest = results[0];
        const previous = results[1];

        const change24h = latest.current_price - previous.current_price;
        const changePercent24h = (change24h / previous.current_price) * 100;

        return {
            currentPrice: latest.current_price,
            change24h,
            changePercent24h,
            volume24h: latest.volume_24h,
            high24h: latest.high_24h,
            low24h: latest.low_24h,
            rsi: latest.rsi || 50,
        };
    } catch (error) {
        console.error('DB_ERROR: Failed to fetch Bitcoin metrics:', error);
        throw error;
    }
}

/**
 * Get historical Bitcoin prices for charting
 */
export async function getHistoricalPrices(
    days: number = 30
): Promise<BitcoinPrice[]> {
    const config = getDatabricksConfig();

    try {
        const query = `
      SELECT 
        date_prices as date,
        open as open,
        high as high,
        low as low,
        close as close,
        volume
      FROM prod.dlh_silver__crypto_prices.obt_fact_day_btc
      WHERE date_prices >= DATEADD(day, -${days}, CURRENT_DATE())
      ORDER BY date_prices ASC
    `;

        const results = await executeQuery<BitcoinPrice>(query, config);
        return results;
    } catch (error) {
        console.error('Failed to fetch historical prices:', error);
        throw error;
    }
}

/**
 * Get aggregated data (weekly, monthly, etc.)
 */
export async function getAggregatedData(
    aggregation: 'weekly' | 'monthly' | 'quarterly' = 'weekly'
): Promise<AggregatedData[]> {
    const config = getDatabricksConfig();

    try {
        // Map aggregation period to table name suffix
        const tableSuffix = aggregation === 'weekly' ? 'week'
            : aggregation === 'monthly' ? 'month'
                : aggregation === 'quarterly' ? 'quarter'
                    : 'week';

        const tableName = `prod.dlh_gold__crypto_prices.agg_${tableSuffix}_btc`;

        // Determine date column based on aggregation
        const dateCol = aggregation === 'weekly' ? 'iso_week_start_date'
            : aggregation === 'monthly' ? 'month_start_date'
                : aggregation === 'quarterly' ? 'quarter_start_date'
                    : 'iso_week_start_date';

        const query = `
      SELECT 
        ${dateCol} as period,
        close as avgPrice,
        high as maxPrice,
        low as minPrice,
        0 as totalVolume
      FROM ${tableName}
      ORDER BY ${dateCol} DESC
      LIMIT 12
    `;

        const results = await executeQuery<AggregatedData>(query, config);
        return results;
    } catch (error) {
        console.error('DB_ERROR: Failed to fetch aggregated data:', error);
        throw error;
    }
}
