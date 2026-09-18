import { executeQuery } from './postgres';
import type { ForecastEmission, ForecastResponse } from './forecast-types';

type StoredEmission = { id: string; emission_date: string; origin_week: string; status: ForecastEmission['status']; payload: { fx: ForecastEmission['fx']; points: Array<Record<string, unknown>> } };

export async function readForecast(currency: string, asOf: string): Promise<ForecastResponse> {
    if (process.env.RAILWAY_ENVIRONMENT_NAME?.toLowerCase() === 'development' && process.env.FORECAST_RESEARCH_PREVIEW === 'true') {
        const { readResearchForecast } = await import('./forecast-research-server');
        return readResearchForecast(currency, asOf);
    }
    const versions = await executeQuery<{ id: string; name: string; withdrawn: boolean }>(
        `SELECT v.id, v.manifest->>'candidate' AS name, v.withdrawn
         FROM forecast.publication p JOIN forecast.versions v ON v.id=p.active_version`);
    const version = versions[0];
    if (!version) return { status: 'absent', model: null, emissions: [] };
    const model = { id: version.id, name: version.name || version.id };
    if (version.withdrawn) return { status: 'withdrawn', model, emissions: [] };
    const rows = await executeQuery<StoredEmission>(
        `SELECT id, emission_date::text, origin_week::text, status, payload FROM forecast.emissions
         WHERE version_id=$1 AND emission_date <= $2::date ORDER BY emission_date DESC, created_at DESC LIMIT 3`, [version.id, asOf]);
    if (!rows.length) return { status: 'absent', model, emissions: [] };
    const emissions: ForecastEmission[] = [];
    for (const row of rows) {
        if (!row.payload || !Array.isArray(row.payload.points) || row.payload.points.length !== 52) return { status: 'invalid', model, emissions: [] };
        const validDate = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value;
        if (!validDate(row.origin_week) || !validDate(row.emission_date) || new Date(row.origin_week).getUTCDay() !== 1 || !['valid', 'delayed', 'invalidated'].includes(row.status) || !row.payload.fx) return { status: 'invalid', model, emissions: [] };
        const fx: ForecastEmission['fx'] = {};
        for (const [code, value] of Object.entries(row.payload.fx)) {
            if (!['EUR', 'CHF'].includes(code) || !value || !Number.isFinite(value.rate) || value.rate <= 0 || !validDate(value.date) || value.date > row.emission_date) return { status: 'invalid', model, emissions: [] };
            fx[code] = { rate: value.rate, date: value.date };
        }
        if (currency !== 'USD' && !fx[currency]) return { status: 'invalid', model, emissions: [] };
        const origin = new Date(`${row.origin_week}T00:00:00Z`);
        origin.setUTCDate(origin.getUTCDate() + 6);
        const points: ForecastEmission['points'] = [];
        for (const [index, point] of row.payload.points.entries()) {
            const values = point[currency];
            const usd = point.USD;
            const expected = new Date(origin);
            expected.setUTCDate(expected.getUTCDate() + (index + 1) * 7);
            if (!Array.isArray(values) || values.length !== 5 || values.some((v, i) => !Number.isFinite(v) || v <= 0 || i > 0 && v < values[i - 1]) || point.horizon_weeks !== index + 1 || point.target_date !== expected.toISOString().slice(0, 10)) return { status: 'invalid', model, emissions: [] };
            const rate = currency === 'USD' ? 1 : fx[currency].rate;
            if (!Array.isArray(usd) || usd.length !== 5 || usd.some((v, i) => !Number.isFinite(v) || v <= 0 || Math.abs(values[i] - v * rate) > Math.abs(v * rate) * 1e-10)) return { status: 'invalid', model, emissions: [] };
            points.push({ horizonWeeks: index + 1, targetDate: point.target_date as string, q25: values[1], q50: values[2], q75: values[3] });
        }
        emissions.push({ id: row.id, emissionDate: row.emission_date, originWeek: row.origin_week, originDate: origin.toISOString().slice(0, 10), status: row.status, fx, points });
    }
    const age = Date.parse(asOf) - Date.parse(emissions[0].emissionDate);
    return { status: age > 8 * 86400000 ? 'stale' : 'available', model, emissions };
}
