import { z } from 'zod';

export const BitcoinMetricsSchema = z.object({
    currentPrice: z.number(),
    change24h: z.number(),
    changePercent24h: z.number(),
    volume24h: z.number(),
    high24h: z.number(),
    low24h: z.number(),
    rsi: z.number(),
});

export const BitcoinPriceSchema = z.object({
    date: z.any().transform(val => (val instanceof Date ? val.toISOString() : String(val))),
    open: z.coerce.number().default(0),
    high: z.coerce.number().default(0),
    low: z.coerce.number().default(0),
    close: z.coerce.number().default(0),
    volume: z.coerce.number().default(0),
    rsi: z.coerce.number().default(50),
    rsi_status: z.string().default('Neutral'),
});

export const BitcoinHistorySchema = z.array(BitcoinPriceSchema);

export const AggregatedDataSchema = z.object({
    period: z.any().transform(val => (val instanceof Date ? val.toISOString() : String(val))),
    avgPrice: z.coerce.number().default(0),
    maxPrice: z.coerce.number().default(0),
    minPrice: z.coerce.number().default(0),
    totalVolume: z.coerce.number().default(0),
});

export const AggregatedDataListSchema = z.array(AggregatedDataSchema);

export type BitcoinPrice = z.infer<typeof BitcoinPriceSchema>;
export type BitcoinMetrics = z.infer<typeof BitcoinMetricsSchema>;
export type AggregatedData = z.infer<typeof AggregatedDataSchema>;

export const BitcoinForecastSchema = z.object({
    date_prices: z.any().transform(val => (val instanceof Date ? val.toISOString() : String(val))),
    predicted_close_usd: z.coerce.number(),
    predicted_close_usd_lower: z.coerce.number(),
    predicted_close_usd_upper: z.coerce.number(),
    predicted_at: z.any().transform(val => (val instanceof Date ? val.toISOString() : String(val))),
});

export type BitcoinForecast = z.infer<typeof BitcoinForecastSchema>;

export const BitcoinSearchParamsSchema = z.object({
    type: z.enum(['metrics', 'history', 'aggregated', 'forecast']),
    days: z.string().optional().transform(val => (val ? parseInt(val) : 30)),
    startDate: z.string().optional(),
    endDate: z.string().optional(),
    period: z.enum(['weekly', 'monthly', 'quarterly']).optional().default('weekly'),
});
