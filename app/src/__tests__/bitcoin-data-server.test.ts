/**
 * Unit tests for Bitcoin API functions
 */

import {
    getCurrentBitcoinMetrics,
    getHistoricalPrices,
    getAggregatedData,
} from '@/lib/bitcoin-data-server';
import {
    BitcoinMetrics,
    BitcoinPrice,
} from '@/lib/schemas';


// Mock the databricks module
jest.mock('@/lib/databricks', () => ({
    executeQuery: jest.fn(),
    getDatabricksConfig: jest.fn(() => ({
        host: 'https://test.databricks.com',
        token: 'test-token',
        httpPath: '/sql/1.0/warehouses/test',
    })),
}));

import { executeQuery } from '@/lib/databricks';

describe('Bitcoin API', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        // Suppress console.error during tests to keep output clean
        jest.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    describe('getCurrentBitcoinMetrics', () => {
        it('should return current Bitcoin metrics with correct calculations', async () => {
            // Mock query response (matches the aliases in the query)
            const mockData = [
                {
                    current_price: 43500,
                    high_24h: 44000,
                    low_24h: 42000,
                    volume_24h: 30000000000,
                    rsi: 65,
                },
                {
                    current_price: 42000,
                    high_24h: 42500,
                    low_24h: 41500,
                    volume_24h: 28000000000,
                    rsi: 60,
                },
            ];

            (executeQuery as jest.Mock).mockResolvedValue(mockData);

            const result = await getCurrentBitcoinMetrics();

            expect(result).toMatchObject({
                currentPrice: 43500,
                change24h: 1500,
                changePercent24h: expect.closeTo(3.57, 1),
                volume24h: 30000000000,
                high24h: 44000,
                low24h: 42000,
                rsi: 65,
            });
        });

        it('should throw error when query fails', async () => {
            (executeQuery as jest.Mock).mockRejectedValue(new Error('Connection failed'));

            await expect(getCurrentBitcoinMetrics()).rejects.toThrow('Connection failed');
        });

        it('should throw error when data is insufficient', async () => {
            (executeQuery as jest.Mock).mockResolvedValue([{ close_usd: 43500 }]);

            await expect(getCurrentBitcoinMetrics()).rejects.toThrow('Insufficient data to calculate metrics');
        });
    });

    describe('getHistoricalPrices', () => {
        it('should return historical price data for specified days', async () => {
            const mockPrices = Array.from({ length: 30 }, (_, i) => ({
                date_prices: `2024-01-${String(i + 1).padStart(2, '0')}`,
                open_usd: 42000 + i * 100,
                high_usd: 43000 + i * 100,
                low_usd: 41000 + i * 100,
                close_usd: 42500 + i * 100,
                volume: 25000000000,
                rsi: 50,
                rsi_status: 'Neutral',
            }));

            (executeQuery as jest.Mock).mockResolvedValue(mockPrices);

            const result = await getHistoricalPrices(30);

            expect(result).toHaveLength(30);
            expect(result[0]).toMatchObject({
                date: expect.any(String),
                open: expect.any(Number),
                high: expect.any(Number),
                low: expect.any(Number),
                close: expect.any(Number),
                volume: expect.any(Number),
            });
        });

        it('should validate OHLC data integrity', async () => {
            const mockPrices = [
                {
                    date_prices: '2024-01-01',
                    open_usd: 42000,
                    high_usd: 43000,
                    low_usd: 41000,
                    close_usd: 42500,
                    volume: 25000000000,
                    rsi: 50,
                    rsi_status: 'Neutral',
                },
            ];

            (executeQuery as jest.Mock).mockResolvedValue(mockPrices);

            const result = await getHistoricalPrices(1);

            expect(result[0].high).toBeGreaterThanOrEqual(result[0].open);
            expect(result[0].high).toBeGreaterThanOrEqual(result[0].close);
            expect(result[0].low).toBeLessThanOrEqual(result[0].open);
            expect(result[0].low).toBeLessThanOrEqual(result[0].close);
        });

        it('should throw error when query fails', async () => {
            (executeQuery as jest.Mock).mockRejectedValue(new Error('Query failed'));

            await expect(getHistoricalPrices(7)).rejects.toThrow('Query failed');
        });
    });

    describe('getAggregatedData', () => {
        it('should return weekly aggregated data', async () => {
            const mockAggregated = [
                {
                    period: '2024-W01',
                    avgPrice: 42500,
                    maxPrice: 44000,
                    minPrice: 41000,
                    totalVolume: 175000000000,
                },
            ];

            (executeQuery as jest.Mock).mockResolvedValue(mockAggregated);

            const result = await getAggregatedData('weekly');

            expect(result).toHaveLength(1);
            expect(result[0]).toMatchObject({
                period: '2024-W01',
                avgPrice: 42500,
                maxPrice: 44000,
                minPrice: 41000,
                totalVolume: 175000000000,
            });
        });

        it('should handle different aggregation periods', async () => {
            (executeQuery as jest.Mock).mockResolvedValue([]);

            await getAggregatedData('monthly');
            expect(executeQuery).toHaveBeenCalledWith(
                expect.stringContaining('prod.dlh_gold__crypto_prices.agg_month_btc')
            );

            await getAggregatedData('quarterly');
            expect(executeQuery).toHaveBeenCalledWith(
                expect.stringContaining('prod.dlh_gold__crypto_prices.agg_quarter_btc')
            );
        });

        it('should throw error when query fails', async () => {
            (executeQuery as jest.Mock).mockRejectedValue(new Error('Table not found'));

            await expect(getAggregatedData('weekly')).rejects.toThrow('Table not found');
        });
    });

    describe('Data validation', () => {
        it('should ensure all prices are positive numbers', async () => {
            const mockPrices = [
                {
                    date: '2024-01-01',
                    open: 42000,
                    high: 43000,
                    low: 41000,
                    close: 42500,
                    volume: 25000000000,
                    rsi: 50,
                    rsi_status: 'Neutral',
                },
            ];

            (executeQuery as jest.Mock).mockResolvedValue(mockPrices);

            const result = await getHistoricalPrices(1);

            expect(result[0].open).toBeGreaterThan(0);
            expect(result[0].high).toBeGreaterThan(0);
            expect(result[0].low).toBeGreaterThan(0);
            expect(result[0].close).toBeGreaterThan(0);
            expect(result[0].volume).toBeGreaterThan(0);
        });

        it('should ensure dates are properly formatted', async () => {
            const mockPrices = [
                {
                    date: '2024-01-15',
                    open: 42000,
                    high: 43000,
                    low: 41000,
                    close: 42500,
                    volume: 25000000000,
                    rsi: 50,
                    rsi_status: 'Neutral',
                },
            ];

            (executeQuery as jest.Mock).mockResolvedValue(mockPrices);

            const result = await getHistoricalPrices(1);

            expect(result[0].date).toMatch(/^\d{4}-\d{2}-\d{2}/);
        });
    });
});
