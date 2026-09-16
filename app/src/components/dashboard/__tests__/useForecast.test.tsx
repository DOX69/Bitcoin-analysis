import { renderHook, waitFor } from '@testing-library/react';
import { useForecast } from '../useForecast';

const points = Array.from({ length: 52 }, (_, i) => ({ horizonWeeks: i + 1, targetDate: new Date(Date.UTC(2026, 8, 13 + i * 7)).toISOString().slice(0, 10), q10: 60, q25: 80, q50: 100, q75: 120, q90: 140 }));
const payload = { status: 'available', model: { id: 'v1', name: 'Published' }, emissions: [{ id: 'e1', emissionDate: '2026-09-07', originWeek: '2026-08-31', originDate: '2026-09-06', fx: { EUR: { rate: 0.9, date: '2026-09-07' } }, status: 'valid', points }] };
beforeEach(() => { global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => payload }); });

it('keeps all 365 daily dates, including the first day, without weekly resampling', async () => {
    const dailyPoints = Array.from({ length: 365 }, (_, i) => ({ horizonDays: i + 1, targetDate: new Date(Date.parse('2026-09-06') + (i + 1) * 86400000).toISOString().slice(0, 10), q25: 80 + i, q50: 100 + i, q75: 120 + i }));
    (fetch as jest.Mock).mockResolvedValue({ ok: true, json: async () => ({ ...payload, frequency: 'daily', emissions: [{ ...payload.emissions[0], points: dailyPoints }] }) });
    const { result } = renderHook(() => useForecast(true, 'USD', '', ''));
    await waitFor(() => expect(result.current.status).toBe('available'));
    expect(result.current.frequency).toBe('daily');
    expect(result.current.projection.emissions[0].points).toHaveLength(365);
    expect(result.current.projection.emissions[0].points[0]).toEqual({ date: '2026-09-07', low: 80, median: 100, high: 120 });
    expect(result.current.projection.emissions[0].points[364].date).toBe('2027-09-06');
});

it('rejects weekly points mislabeled as daily', async () => {
    (fetch as jest.Mock).mockResolvedValue({ ok: true, json: async () => ({ ...payload, frequency: 'daily' }) });
    const { result } = renderHook(() => useForecast(true, 'USD', '', ''));
    await waitFor(() => expect(result.current.status).toBe('invalid'));
    expect(result.current.projection.emissions).toEqual([]);
});

it('fetches only when enabled and preserves frozen values and weekly dates', async () => {
    const { result, rerender } = renderHook(({ enabled }) => useForecast(enabled, 'EUR', '', ''), { initialProps: { enabled: false } });
    expect(fetch).not.toHaveBeenCalled();
    rerender({ enabled: true });
    await waitFor(() => expect(result.current.status).toBe('available'));
    expect(fetch).toHaveBeenCalledWith('/api/forecast?currency=EUR', expect.anything());
    expect(result.current.projection.emissions[0].points[0]).toEqual({ date: '2026-09-13', low: 80, median: 100, high: 120 });
});
it('excludes emissions issued after a past period and does not project beyond it', async () => {
    const { result } = renderHook(() => useForecast(true, 'USD', '2026-08-01', '2026-09-01'));
    await waitFor(() => expect(result.current.status).toBe('available'));
    expect(result.current.projection.emissions).toEqual([]);
    expect(fetch).toHaveBeenCalledWith('/api/forecast?currency=USD&asOf=2026-09-01', expect.anything());
});
it('rejects malformed quantiles instead of plotting them', async () => {
    (fetch as jest.Mock).mockResolvedValue({ ok: true, json: async () => ({ ...payload, emissions: [{ ...payload.emissions[0], points: [{ ...points[0], q25: 500 }] }] }) });
    const { result } = renderHook(() => useForecast(true, 'USD', '', ''));
    await waitFor(() => expect(result.current.status).toBe('invalid'));
    expect(result.current.projection.emissions).toEqual([]);
});
it('clears previous currency values immediately during a new request', async () => {
    const { result, rerender } = renderHook(({ currency }: { currency: 'USD' | 'CHF' }) => useForecast(true, currency, '', ''), { initialProps: { currency: 'USD' } });
    await waitFor(() => expect(result.current.status).toBe('available'));
    (fetch as jest.Mock).mockReturnValue(new Promise(() => {}));
    rerender({ currency: 'CHF' });
    expect(result.current.status).toBe('loading');
    expect(result.current.projection.emissions).toEqual([]);
});
it('distinguishes network errors from absence', async () => {
    (fetch as jest.Mock).mockRejectedValue(new Error('offline'));
    const { result } = renderHook(() => useForecast(true, 'USD', '', ''));
    await waitFor(() => expect(result.current.status).toBe('error'));
});
it('extends a range ending today through all 52 future horizons', async () => {
    const today = new Date().toISOString().slice(0, 10);
    const { result } = renderHook(() => useForecast(true, 'USD', '', today));
    await waitFor(() => expect(result.current.status).toBe('available'));
    expect(result.current.projection.emissions[0].points).toHaveLength(52);
});
it('removes an invalidated curve while keeping its explicit status', async () => {
    (fetch as jest.Mock).mockResolvedValue({ ok: true, json: async () => ({ ...payload, emissions: [{ ...payload.emissions[0], status: 'invalidated', points: [] }] }) });
    const { result } = renderHook(() => useForecast(true, 'USD', '', ''));
    await waitFor(() => expect(result.current.status).toBe('available'));
    expect(result.current.emissions[0].status).toBe('invalidated');
    expect(result.current.projection.emissions).toEqual([]);
});
it('preserves the original curve for a delayed emission', async () => {
    (fetch as jest.Mock).mockResolvedValue({ ok: true, json: async () => ({ ...payload, emissions: [{ ...payload.emissions[0], status: 'delayed' }] }) });
    const { result } = renderHook(() => useForecast(true, 'USD', '', ''));
    await waitFor(() => expect(result.current.status).toBe('available'));
    expect(result.current.emissions[0].status).toBe('delayed');
    expect(result.current.projection.emissions[0].issued).toBe('2026-09-07');
    expect(result.current.projection.emissions[0].points[0].median).toBe(100);
});

