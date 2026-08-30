import { GET } from '@/app/api/bitcoin/route';
import { getHistoricalPrices } from '@/lib/bitcoin-data-server';

jest.mock('next/server', () => ({
    NextResponse: {
        json: (body: unknown, init?: { status?: number }) => ({
            status: init?.status ?? 200,
            json: async () => body,
        }),
    },
}));

jest.mock('@/lib/bitcoin-data-server', () => ({
    getCurrentBitcoinMetrics: jest.fn(),
    getHistoricalPrices: jest.fn().mockResolvedValue([]),
    getAggregatedData: jest.fn(),
}));

const request = (query: string) => ({
    url: `http://localhost/api/bitcoin?${query}`,
}) as Request;

describe('Bitcoin API query validation', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('defaults days to 30 when omitted', async () => {
        const response = await GET(request('type=history'));

        expect(response.status).toBe(200);
        expect(getHistoricalPrices).toHaveBeenCalledWith(30, undefined, undefined);
    });

    it.each(['1', '3650'] as const)('accepts days=%s', async days => {
        const response = await GET(request(`type=history&days=${days}`));

        expect(response.status).toBe(200);
        expect(getHistoricalPrices).toHaveBeenCalledWith(Number(days), undefined, undefined);
    });

    it.each(['', '0', '-1', '1.5', '30days', '3651'])('rejects invalid days=%s', async days => {
        const response = await GET(request(`type=history&days=${encodeURIComponent(days)}`));

        expect(response.status).toBe(400);
        expect(getHistoricalPrices).not.toHaveBeenCalled();
    });

    it.each([
        ['2024-02-29', '2024-02-29'],
        ['2020-01-01', '2029-12-29'],
    ])('accepts the valid date range %s to %s', async (startDate, endDate) => {
        const response = await GET(request(
            `type=history&startDate=${startDate}&endDate=${endDate}`
        ));

        expect(response.status).toBe(200);
        expect(getHistoricalPrices).toHaveBeenCalledWith(30, startDate, endDate);
    });

    it.each([
        'type=history&startDate=2024-01-01',
        'type=history&endDate=2024-01-01',
        'type=history&startDate=2024-1-01&endDate=2024-01-02',
        'type=history&startDate=2024-02-30&endDate=2024-03-01',
        'type=history&startDate=2024-03-02&endDate=2024-03-01',
        'type=history&startDate=2020-01-01&endDate=2029-12-30',
    ])('rejects the invalid date query %s', async query => {
        const response = await GET(request(query));

        expect(response.status).toBe(400);
        expect(getHistoricalPrices).not.toHaveBeenCalled();
    });
});
