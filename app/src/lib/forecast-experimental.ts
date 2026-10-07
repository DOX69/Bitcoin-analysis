import { z } from 'zod';
import { executeQuery } from './postgres';
import type { ForecastResponse } from './forecast-types';

const day = z.iso.date();
const quantiles = z.array(z.number().positive()).length(5).refine(values => values.every((v, i) => i === 0 || v >= values[i - 1]));
const schema = z.object({
    id: day, emissionDate: day, issuedAt: z.iso.datetime({ offset: true }), originWeek: day, originDate: day, horizonEnd: day,
    status: z.enum(['valid', 'delayed']),
    fx: z.object({ EUR: z.object({ rate: z.number().positive(), date: day }), CHF: z.object({ rate: z.number().positive(), date: day }) }),
    points: z.array(z.object({ horizonWeeks: z.number().int().positive(), targetDate: day, USD: quantiles, EUR: quantiles, CHF: quantiles })).min(25).max(27),
}).superRefine((value, context) => {
    const fail = () => context.addIssue({ code: 'custom', message: 'Invalid experimental emission' });
    const issued = new Date(value.emissionDate);
    const end = new Date(Date.UTC(issued.getUTCFullYear(), issued.getUTCMonth() + 7, 0));
    end.setUTCDate(Math.min(issued.getUTCDate(), end.getUTCDate()));
    if (end.toISOString().slice(0, 10) !== value.horizonEnd || value.issuedAt.slice(0, 10) !== value.emissionDate || value.id !== value.originWeek || new Date(value.originWeek).getUTCDay() !== 1 || Date.parse(value.originDate) !== Date.parse(value.originWeek) + 6 * 86400000 || ![1, 2].includes(issued.getUTCDay()) || ![1, 2].includes((Date.parse(value.emissionDate) - Date.parse(value.originDate)) / 86400000)) fail();
    for (const currency of ['EUR', 'CHF'] as const) {
        if (value.fx[currency].date > value.emissionDate) fail();
    }
    value.points.forEach((point, i) => {
        if (point.horizonWeeks !== i + 1 || Date.parse(point.targetDate) !== Date.parse(value.originDate) + (i + 1) * 7 * 86400000 || point.targetDate <= value.emissionDate || point.targetDate > value.horizonEnd) fail();
        for (const currency of ['EUR', 'CHF'] as const) {
            if (point[currency].some((v, j) => Math.abs(v - point.USD[j] * value.fx[currency].rate) > Math.abs(v) * 1e-10)) fail();
        }
    });
    if (Date.parse(value.points[value.points.length - 1].targetDate) + 7 * 86400000 <= Date.parse(value.horizonEnd)) fail();
});

export async function readExperimentalForecast(currency: string, asOf: string): Promise<ForecastResponse> {
    const sha = process.env.FORECAST_EXPERIMENTAL_MODEL_SHA256;
    if (!sha || !/^[a-f0-9]{64}$/.test(sha)) return { status: 'absent', model: null, emissions: [] };
    const model = { id: `experimental-${sha}`, name: 'lightgbm_quantile', experimental: true, horizonMonths: 6 as const };
    const rows = await executeQuery<{ payload: unknown }>(
        `SELECT payload FROM forecast_experimental.emissions WHERE model_sha256=$1 AND emission_date <= $2::date ORDER BY emission_date DESC LIMIT 3`, [sha, asOf]);
    if (!rows.length) return { status: 'absent', model, emissions: [] };
    const emissions: ForecastResponse['emissions'] = [];
    for (const row of rows) {
        const parsed = schema.safeParse(row.payload);
        if (!parsed.success || parsed.data.emissionDate > asOf) return { status: 'invalid', model, emissions: [] };
        const value = parsed.data;
        emissions.push({ id: value.id, emissionDate: value.emissionDate, issuedAt: value.issuedAt, originWeek: value.originWeek, originDate: value.originDate, horizonEnd: value.horizonEnd, status: value.status, fx: value.fx,
            points: value.points.map(p => {
                const q = p[currency as 'USD' | 'EUR' | 'CHF'];
                return { horizonWeeks: p.horizonWeeks, targetDate: p.targetDate, q10: q[0], q25: q[1], q50: q[2], q75: q[3], q90: q[4] };
            }),
        });
    }
    return { status: Date.parse(asOf) - Date.parse(emissions[0].emissionDate) > 8 * 86400000 ? 'stale' : 'available', model, emissions };
}
