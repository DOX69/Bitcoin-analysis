import { GetObjectCommand, ListObjectsV2Command, S3Client } from '@aws-sdk/client-s3';
import { z } from 'zod';
import { executeQuery } from './postgres';
import type { ForecastEmission, ForecastResponse } from './forecast-types';

const prefix = 'development/research/damped-trend-v1/emissions/';
const quantiles = z.array(z.number().positive()).length(5).refine(values => values.every((v, i) => i === 0 || v >= values[i - 1]));
const envelopeSchema = z.object({ emission: z.object({
    created_at: z.iso.datetime({ offset: true }), origin_week: z.iso.date(),
    currency: z.literal('USD'), evidence: z.literal('prospective'),
    model_manifest_sha256: z.literal('f20851a615ece5351b0312e018b4fec1aed18cb1af9655370962a593c7c2382b'),
    points: z.array(z.object({ horizon_weeks: z.number().int(), target_date: z.iso.date(), USD: quantiles })).length(52),
}) });

export function researchPreviewEnabled() {
    return process.env.RAILWAY_ENVIRONMENT_NAME?.toLowerCase() === 'development' && process.env.FORECAST_RESEARCH_PREVIEW === 'true';
}

export async function readResearchForecast(currency: string, asOf: string): Promise<ForecastResponse> {
    if (!researchPreviewEnabled()) throw new Error('Research preview is restricted to Development');
    const bucket = process.env.FORECAST_RESEARCH_BUCKET;
    const endpoint = process.env.FORECAST_S3_ENDPOINT_URL;
    if (!bucket || !endpoint) throw new Error('Research storage missing');
    const client = new S3Client({ endpoint, region: process.env.AWS_DEFAULT_REGION ?? 'auto', maxAttempts: 2 });
    const requestOptions = { abortSignal: AbortSignal.timeout(10000) };
    const objectKeys: string[] = [];
    let token: string | undefined;
    do {
        const page = await client.send(new ListObjectsV2Command({ Bucket: bucket, Prefix: prefix, ContinuationToken: token }), requestOptions);
        for (const item of page.Contents ?? []) {
            if (item.Key && /^\d{4}-\d{2}-\d{2}\.json$/.test(item.Key.slice(prefix.length)) && item.Key.slice(prefix.length, -5) <= asOf) objectKeys.push(item.Key);
        }
        token = page.IsTruncated ? page.NextContinuationToken : undefined;
    } while (token);
    const model = { id: 'research-damped-trend-v1', name: 'Tendance amortie expérimentale' };
    const emissions: ForecastEmission[] = [];
    try {
        for (const key of objectKeys.sort().reverse()) {
            const object = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key }), requestOptions);
            const { emission } = envelopeSchema.parse(JSON.parse(await object.Body!.transformToString()));
            const emissionDate = emission.created_at.slice(0, 10);
            if (emissionDate > asOf) continue;
            const origin = Date.parse(emission.origin_week);
            if (new Date(origin).getUTCDay() !== 1 || key !== `${prefix}${emission.origin_week}.json`) throw new Error('Invalid research origin');
            const originDate = new Date(origin + 6 * 86400000).toISOString().slice(0, 10);
            if (Date.parse(emission.created_at) <= Date.parse(originDate) + 86400000 - 1) throw new Error('Incomplete research week');
            const fx: ForecastEmission['fx'] = {};
            if (currency !== 'USD') {
                const table = currency === 'EUR' ? 'usd_eur_rates' : currency === 'CHF' ? 'usd_chf_rates' : null;
                if (!table) throw new Error('Invalid currency');
                const [rate] = await executeQuery<{ rate: number; date: string }>(
                    `SELECT rate::double precision, date::text FROM bronze.${table} WHERE date <= $1::date AND ingest_date_time <= $2::timestamptz ORDER BY date DESC, ingest_date_time DESC LIMIT 1`, [emissionDate, emission.created_at]);
                if (!rate || !Number.isFinite(rate.rate) || rate.rate <= 0) throw new Error('Research FX missing');
                fx[currency] = rate;
            }
            const multiplier = currency === 'USD' ? 1 : fx[currency].rate;
            const points = emission.points.map((point, index) => {
                if (point.horizon_weeks !== index + 1 || Date.parse(point.target_date) !== Date.parse(originDate) + (index + 1) * 7 * 86400000) throw new Error('Invalid research target');
                return { horizonWeeks: index + 1, targetDate: point.target_date, q25: point.USD[1] * multiplier, q50: point.USD[2] * multiplier, q75: point.USD[3] * multiplier };
            });
            emissions.push({ id: `research-${emission.origin_week}`, emissionDate, originWeek: emission.origin_week, originDate, status: 'valid', fx, points });
            if (emissions.length === 3) break;
        }
    } finally { client.destroy(); }
    return { status: !emissions.length ? 'absent' : Date.parse(asOf) - Date.parse(emissions[0].emissionDate) > 8 * 86400000 ? 'stale' : 'available', model, emissions, experimental: true };
}
