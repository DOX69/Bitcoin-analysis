import { getHistoricalPrices } from '@/lib/bitcoin-data-server';
import { executeQuery } from '@/lib/databricks';

// Mock the databricks module
jest.mock('@/lib/databricks', () => ({
    executeQuery: jest.fn(),
    getDatabricksConfig: jest.fn(() => ({
        host: 'https://test.databricks.com',
        token: 'test-token',
        httpPath: '/sql/1.0/warehouses/test',
    })),
}));

describe('Performance Benchmark', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        // Suppress console.error
        jest.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    it('should measure execution time of getHistoricalPrices', async () => {
        // Mock implementation with delays
        (executeQuery as jest.Mock).mockImplementation(async (query: string) => {
            if (query.includes('usd_to_other')) {
                // Currency query
                await new Promise(resolve => setTimeout(resolve, 50));
                return [{ rate_usd_chf: 0.9, rate_usd_eur: 0.92 }];
            } else {
                // Prices query
                await new Promise(resolve => setTimeout(resolve, 100));
                // Return dummy data
                return Array.from({ length: 30 }, (_, i) => ({
                    date: `2024-01-${String(i + 1).padStart(2, '0')}`,
                    open: 100,
                    high: 110,
                    low: 90,
                    close: 105,
                    volume: 1000,
                    rsi: 50,
                    rsi_status: 'Neutral',
                }));
            }
        });

        const startTime = Date.now();
        await getHistoricalPrices(30, undefined, undefined, 'EUR');
        const endTime = Date.now();
        const duration = endTime - startTime;

        // Optimized expectation: around 100ms (max(100, 50)) + overhead
        // Should be significantly less than 150ms
        expect(duration).toBeLessThan(140);
        expect(duration).toBeGreaterThanOrEqual(100);
    });
});
