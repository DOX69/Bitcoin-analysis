/** @jest-environment node */
jest.mock('@/lib/postgres', () => ({ executeQuery: jest.fn() }));
import { executeQuery } from '@/lib/postgres';
import { GET } from '@/app/api/forecast/route';
const query = jest.mocked(executeQuery);
test('rejects invalid currency without accessing database', async () => {
    const response = await GET(new Request('http://localhost/api/forecast?currency=BAD'));
    expect(response.status).toBe(400);
    expect(query).not.toHaveBeenCalled();
});
test('absent is explicit', async () => {
    query.mockResolvedValueOnce([]);
    const response = await GET(new Request('http://localhost/api/forecast'));
    expect(await response.json()).toEqual({ status: 'absent', model: null, emissions: [] });
});
test('withdrawn version does not expose manifests or artifact locations', async () => {
    query.mockResolvedValueOnce([{ id: 'v1', name: 'test', withdrawn: true, artifact_prefix: 'secret' }]);
    const response = await GET(new Request('http://localhost/api/forecast'));
    expect(await response.json()).toEqual({ status: 'withdrawn', model: { id: 'v1', name: 'test' }, emissions: [] });
});
test('database failure returns generic unavailable response', async () => {
    query.mockRejectedValueOnce(new Error('database secret'));
    const response = await GET(new Request('http://localhost/api/forecast'));
    expect(response.status).toBe(503);
    expect(JSON.stringify(await response.json())).not.toContain('secret');
});

function stored() {
    return { id: 'e1', emission_date: '2026-09-07', origin_week: '2026-08-31', status: 'delayed', payload: { fx: { EUR: { rate: .9, date: '2026-09-07' } }, points: Array.from({ length: 52 }, (_, i) => ({ horizon_weeks: i + 1, target_date: new Date(Date.UTC(2026, 8, 6 + 7 * (i + 1))).toISOString().slice(0, 10), USD: [1,2,3,4,5], EUR: [.9,1.8,2.7,3.6,4.5] })) } };
}
test('returns original frozen quantiles, hides internal quantiles and filters asOf in SQL', async () => {
    query.mockResolvedValueOnce([{ id: 'v1', name: 'test', withdrawn: false }]).mockResolvedValueOnce([stored()]);
    const response = await GET(new Request('http://localhost/api/forecast?currency=EUR&asOf=2026-09-09'));
    const body = await response.json();
    expect(body.status).toBe('available');
    expect(body.emissions[0].points[0]).toEqual({ horizonWeeks: 1, targetDate: '2026-09-13', q25: 1.8, q50: 2.7, q75: 3.6 });
    expect(query).toHaveBeenLastCalledWith(expect.stringContaining('emission_date <= $2'), ['v1', '2026-09-09']);
});
test('stale emissions remain readable', async () => {
    query.mockResolvedValueOnce([{ id: 'v1', name: 'test', withdrawn: false }]).mockResolvedValueOnce([stored()]);
    const response = await GET(new Request('http://localhost/api/forecast?asOf=2026-09-20'));
    const body = await response.json();
    expect(body.status).toBe('stale');
    expect(body.emissions).toHaveLength(1);
});
test('invalid stored quantiles return invalid without partial curves', async () => {
    const row = stored(); row.payload.points[0].USD = [4,3,2,1,0];
    query.mockResolvedValueOnce([{ id: 'v1', name: 'test', withdrawn: false }]).mockResolvedValueOnce([row]);
    const response = await GET(new Request('http://localhost/api/forecast'));
    expect((await response.json()).status).toBe('invalid');
});
test('corrupt converted values cannot override frozen FX', async () => {
    const row = stored(); row.payload.points[0].EUR = [1,2,3,4,5];
    query.mockResolvedValueOnce([{ id: 'v1', name: 'test', withdrawn: false }]).mockResolvedValueOnce([row]);
    const response = await GET(new Request('http://localhost/api/forecast?currency=EUR'));
    expect((await response.json()).status).toBe('invalid');
});
