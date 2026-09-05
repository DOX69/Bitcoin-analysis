import { z } from 'zod';

const MAX_QUERY_DAYS = 3650;
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000;

function isCalendarDate(value: string): boolean {
    const date = new Date(`${value}T00:00:00.000Z`);
    return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

export const CalendarDateSchema = z.string().regex(DATE_PATTERN).refine(isCalendarDate);
const MarketDateSchema = z.union([
    CalendarDateSchema,
    z.iso.datetime().refine(value => isCalendarDate(value.slice(0, 10))),
    z.date().transform(value => value.toISOString()),
]);
export const SqlNumberSchema = z.union([
    z.number().finite(),
    z.string().trim().min(1).transform(Number),
]).pipe(z.number().finite());
export const CurrencySchema = z.enum(['USD', 'CHF', 'EUR']);

export const BitcoinMetricsSchema = z.object({
    observedAt: CalendarDateSchema.optional(),
    dataAgeDays: z.number().int().nonnegative().optional(),
    currentPrice: z.number().finite(),
    change24h: z.number().finite(),
    changePercent24h: z.number().finite(),
    volume24h: z.number().finite(),
    high24h: z.number().finite(),
    low24h: z.number().finite(),
    rsi: z.number().finite().nullable(),
});

export const BitcoinPriceSchema = z.object({
    date: MarketDateSchema,
    aggregation: z.enum(['daily', 'monthly']).optional(),
    open: SqlNumberSchema,
    high: SqlNumberSchema,
    low: SqlNumberSchema,
    close: SqlNumberSchema,
    volume: SqlNumberSchema,
    rsi: SqlNumberSchema.nullable().optional(),
    rsi_status: z.string().default('Neutral'),
    macd: SqlNumberSchema.nullable().optional(),
    macd_signal: SqlNumberSchema.nullable().optional(),
    macd_hist: SqlNumberSchema.nullable().optional(),
    sma_7: SqlNumberSchema.nullable().optional(),
    sma_50: SqlNumberSchema.nullable().optional(),
    sma_200: SqlNumberSchema.nullable().optional(),
    ema_7: SqlNumberSchema.nullable().optional(),
    ema_50: SqlNumberSchema.nullable().optional(),
    ema_200: SqlNumberSchema.nullable().optional(),
});

export const BitcoinHistorySchema = z.array(BitcoinPriceSchema);

export const AggregatedDataSchema = z.object({
    period: MarketDateSchema,
    avgPrice: SqlNumberSchema,
    maxPrice: SqlNumberSchema,
    minPrice: SqlNumberSchema,
    totalVolume: SqlNumberSchema,
});

export const AggregatedDataListSchema = z.array(AggregatedDataSchema);

export type BitcoinPrice = z.infer<typeof BitcoinPriceSchema>;
export type BitcoinMetrics = z.infer<typeof BitcoinMetricsSchema>;
export type AggregatedData = z.infer<typeof AggregatedDataSchema>;

const dateRangeShape = {
    startDate: CalendarDateSchema.optional(),
    endDate: CalendarDateSchema.optional(),
};

function validateDateRange(maxDays?: number) {
    return (params: { startDate?: string; endDate?: string }, context: z.RefinementCtx) => {
        if ((params.startDate === undefined) !== (params.endDate === undefined)) {
            context.addIssue({ code: 'custom', message: 'startDate and endDate must be provided together',
                path: params.startDate === undefined ? ['startDate'] : ['endDate'] });
            return;
        }
        if (!params.startDate || !params.endDate || !isCalendarDate(params.startDate) || !isCalendarDate(params.endDate)) return;
        const intervalDays = (Date.parse(params.endDate) - Date.parse(params.startDate)) / MILLISECONDS_PER_DAY;
        if (intervalDays < 0 || (maxDays !== undefined && intervalDays > maxDays)) {
            context.addIssue({ code: 'custom', message: maxDays === undefined
                ? 'endDate must be on or after startDate'
                : `Date interval must be between 0 and ${maxDays} days`, path: ['endDate'] });
        }
    };
}

export const BitcoinSearchParamsSchema = z.object({
    type: z.enum(['metrics', 'history', 'aggregated']),
    days: z.string().regex(/^\d+$/).transform(Number)
        .pipe(z.number().int().min(1).max(MAX_QUERY_DAYS)).optional().default(30),
    ...dateRangeShape,
    period: z.enum(['weekly', 'monthly', 'quarterly']).optional().default('weekly'),
}).superRefine(validateDateRange(MAX_QUERY_DAYS));

export const DashboardSearchParamsSchema = z.object({
    time: z.enum(['1w', '1m', '6m', '1y', 'ytd', 'all', 'custom']).optional().default('6m'),
    currency: CurrencySchema.optional().default('USD'),
    ...dateRangeShape,
}).superRefine(validateDateRange()).superRefine((params, context) => {
    if (params.time === 'custom' && (!params.startDate || !params.endDate)) {
        context.addIssue({ code: 'custom', message: 'Custom ranges require both dates', path: ['time'] });
    }
});
