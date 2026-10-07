/** @jest-environment node */
jest.mock('@/lib/postgres', () => ({ executeQuery: jest.fn() }));
import { executeQuery } from '@/lib/postgres';
import { GET } from '@/app/api/forecast/route';
const query = jest.mocked(executeQuery);
const environment = process.env;

function payload() {
    return { id: '2026-09-28', emissionDate: '2026-10-05', issuedAt: '2026-10-05T06:30:00+00:00', originWeek: '2026-09-28', originDate: '2026-10-04', horizonEnd: '2027-04-05', status: 'valid', fx: { EUR: { rate: .9, date: '2026-10-02' }, CHF: { rate: .8, date: '2026-10-02' } }, points: Array.from({ length: 26 }, (_, i) => ({ horizonWeeks: i + 1, targetDate: new Date(Date.UTC(2026, 9, 11 + i * 7)).toISOString().slice(0, 10), USD: [1, 2, 3, 4, 5], EUR: [.9, 1.8, 2.7, 3.6, 4.5], CHF: [.8, 1.6, 2.4, 3.2, 4] })) };
}
beforeEach(() => { process.env = { ...environment, FORECAST_EXPERIMENTAL_ENABLED: 'true', FORECAST_EXPERIMENTAL_MODEL_SHA256: 'a'.repeat(64) }; query.mockReset(); });
afterEach(() => { process.env = environment; });

test('publishes six calendar months with both bands and original emission time', async () => {
    query.mockResolvedValueOnce([{ payload: payload() }]);
    const result = await (await GET(new Request('http://localhost/api/forecast?currency=EUR&asOf=2026-10-07'))).json();
    expect(result.model).toMatchObject({ experimental: true, horizonMonths: 6 });
    expect(result.emissions[0]).toMatchObject({ issuedAt: '2026-10-05T06:30:00+00:00', horizonEnd: '2027-04-05' });
    expect(result.emissions[0].points).toHaveLength(26);
    expect(result.emissions[0].points[0]).toMatchObject({ q10: .9, q25: 1.8, q50: 2.7, q75: 3.6, q90: 4.5 });
    expect(query).toHaveBeenCalledWith(expect.stringContaining('forecast_experimental'), ['a'.repeat(64), '2026-10-07']);
});

test.each(['extra horizon', 'missing horizon', 'changed FX', 'backdated', 'inverted quantiles'])('refuses %s without partial curves', async failure => {
    const data = payload();
    if (failure === 'extra horizon') data.points.push({ ...data.points[25], horizonWeeks: 27, targetDate: '2027-04-11' });
    if (failure === 'missing horizon') data.points.pop();
    if (failure === 'changed FX') data.points[0].EUR[0] = 100;
    if (failure === 'backdated') data.issuedAt = '2026-10-07T06:30:00+00:00';
    if (failure === 'inverted quantiles') data.points[0].USD = [5,4,3,2,1];
    query.mockResolvedValueOnce([{ payload: data }]);
    const result = await (await GET(new Request('http://localhost/api/forecast?asOf=2026-10-07'))).json();
    expect(result.status).toBe('invalid');
    expect(result.emissions).toEqual([]);
});

test('missing pinned model cannot query or publish arbitrary research', async () => {
    delete process.env.FORECAST_EXPERIMENTAL_MODEL_SHA256;
    expect((await (await GET(new Request('http://localhost/api/forecast'))).json()).status).toBe('absent');
    expect(query).not.toHaveBeenCalled();
});
