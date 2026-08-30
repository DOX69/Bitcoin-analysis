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
    rsi: z.coerce.number().nullable().optional(),
    rsi_status: z.string().default('Neutral'),
    macd: z.coerce.number().nullable().optional(),
    macd_signal: z.coerce.number().nullable().optional(),
    macd_hist: z.coerce.number().nullable().optional(),
    sma_7: z.coerce.number().nullable().optional(),
    sma_50: z.coerce.number().nullable().optional(),
    sma_200: z.coerce.number().nullable().optional(),
    ema_7: z.coerce.number().nullable().optional(),
    ema_50: z.coerce.number().nullable().optional(),
    ema_200: z.coerce.number().nullable().optional(),
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

const MAX_QUERY_DAYS = 3650;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;

function isCalendarDate(value: string): boolean {
    const date = new Date(`${value}T00:00:00.000Z`);
    return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

const queryDateSchema = z.string()
    .regex(DATE_PATTERN)
    .refine(isCalendarDate);

export const BitcoinSearchParamsSchema = z.object({
    type: z.enum(['metrics', 'history', 'aggregated']),
    days: z.string()
        .regex(/^\d+$/)
        .transform(Number)
        .pipe(z.number().int().min(1).max(MAX_QUERY_DAYS))
        .optional()
        .default(30),
    startDate: queryDateSchema.optional(),
    endDate: queryDateSchema.optional(),
    period: z.enum(['weekly', 'monthly', 'quarterly']).optional().default('weekly'),
}).superRefine((params, context) => {
    if ((params.startDate === undefined) !== (params.endDate === undefined)) {
        context.addIssue({
            code: 'custom',
            message: 'startDate and endDate must be provided together',
            path: params.startDate === undefined ? ['startDate'] : ['endDate'],
        });
        return;
    }

    if (!params.startDate || !params.endDate ||
        !isCalendarDate(params.startDate) || !isCalendarDate(params.endDate)) {
        return;
    }

    const start = Date.parse(`${params.startDate}T00:00:00.000Z`);
    const end = Date.parse(`${params.endDate}T00:00:00.000Z`);
    const intervalDays = (end - start) / MILLISECONDS_PER_DAY;

    if (intervalDays < 0 || intervalDays > MAX_QUERY_DAYS) {
        context.addIssue({
            code: 'custom',
            message: `Date interval must be between 0 and ${MAX_QUERY_DAYS} days`,
            path: ['endDate'],
        });
    }
});
