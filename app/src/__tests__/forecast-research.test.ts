/** @jest-environment node */
jest.mock('@aws-sdk/client-s3', () => ({ S3Client: jest.fn(), GetObjectCommand: jest.fn(), ListObjectsV2Command: jest.fn() }));
jest.mock('@/lib/postgres', () => ({ executeQuery: jest.fn() }));
import { S3Client } from '@aws-sdk/client-s3';
import { executeQuery } from '@/lib/postgres';
import { readResearchForecast, researchPreviewEnabled } from '@/lib/forecast-research-server';

const send = jest.fn();
const destroy = jest.fn();
const original = { ...process.env };
const key = 'development/research/hybrid-v1/emissions/2026-09-07.json';
function archive() {
    return { emission: { created_at: '2026-09-14T05:24:02.309673+00:00', origin_week: '2026-09-07', currency: 'USD', evidence: 'prospective', model_manifest_sha256: '3c8b3864ce908e1acdbb01c635ddd82eb1f61337b95c2c6a3d04377fb92d24c3', points: Array.from({ length: 52 }, (_, i) => ({ horizon_weeks: i + 1, target_date: new Date(Date.parse('2026-09-13') + (i + 1) * 7 * 86400000).toISOString().slice(0, 10), USD: [80, 90, 100, 110, 120] })) } };
}
function responses(value = archive()) {
    send.mockResolvedValueOnce({ Contents: [{ Key: key }] }).mockResolvedValueOnce({ Body: { transformToString: async () => JSON.stringify(value) } });
}
beforeEach(() => {
    jest.clearAllMocks();
    process.env.RAILWAY_ENVIRONMENT_NAME = 'Development';
    process.env.FORECAST_RESEARCH_PREVIEW = 'true';
    process.env.FORECAST_RESEARCH_BUCKET = 'private-bucket';
    process.env.FORECAST_S3_ENDPOINT_URL = 'https://storage.example';
    jest.mocked(S3Client).mockImplementation(() => ({ send, destroy }) as unknown as S3Client);
});
afterAll(() => { process.env = original; });
test('fails closed in Production even with preview enabled', async () => {
    process.env.RAILWAY_ENVIRONMENT_NAME = 'production';
    expect(researchPreviewEnabled()).toBe(false);
    await expect(readResearchForecast('USD', '2026-09-14')).rejects.toThrow('Development');
    expect(send).not.toHaveBeenCalled();
});
test('serves only the existing prototype quantiles and experimental status', async () => {
    responses();
    const result = await readResearchForecast('USD', '2026-09-14');
    expect(result.experimental).toBe(true);
    expect(result.emissions[0].points).toHaveLength(52);
    expect(result.emissions[0].points[0]).toEqual({ horizonWeeks: 1, targetDate: '2026-09-20', q25: 90, q50: 100, q75: 110 });
    expect(JSON.stringify(result)).not.toMatch(/private-bucket|snapshot|sha256/);
    expect(executeQuery).not.toHaveBeenCalled();
    expect(destroy).toHaveBeenCalled();
});
test('does not expose an emission before its actual creation date', async () => {
    responses();
    expect((await readResearchForecast('USD', '2026-09-13')).emissions).toEqual([]);
});
test('converts with an exchange rate known at emission time', async () => {
    responses();
    jest.mocked(executeQuery).mockResolvedValueOnce([{ rate: 0.9, date: '2026-09-11' }]);
    const result = await readResearchForecast('EUR', '2026-09-14');
    expect(result.emissions[0].points[0].q50).toBe(90);
    expect(result.emissions[0].fx.EUR).toEqual({ rate: 0.9, date: '2026-09-11' });
    expect(executeQuery).toHaveBeenCalledWith(expect.stringContaining('ingest_date_time <= $2'), ['2026-09-14', '2026-09-14T05:24:02.309673+00:00']);
});
test('rejects incorrect target dates instead of drawing a misleading curve', async () => {
    const value = archive();
    value.emission.points[0].target_date = '2026-09-21';
    responses(value);
    await expect(readResearchForecast('USD', '2026-09-14')).rejects.toThrow('target');
});
