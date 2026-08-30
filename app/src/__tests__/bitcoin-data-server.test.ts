/**
 * Unit tests for Bitcoin API functions
 */

import {
    getCurrentBitcoinMetrics,
    getHistoricalPrices,
    getAggregatedData,
    type Currency,
} from '@/lib/bitcoin-data-server';
import {
    BitcoinMetrics,
    BitcoinPrice,
} from '@/lib/schemas';


jest.mock('@/lib/postgres', () => ({
    executeQuery: jest.fn(),
}));

import { executeQuery } from '@/lib/postgres';

describe('Bitcoin API', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        // Suppress console.error during tests to keep output clean
        jest.spyOn(console, 'error').mockImplementation(() => { });
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    describe('getCurrentBitcoinMetrics', () => {
        it('preserves an RSI value of zero', async () => {
            const mockData = [
                {
                    current_price: '43500',
                    high_24h: '44000',
                    low_24h: '42000',
                    volume_24h: '30000000000',
                    rsi: 0,
                },
                {
                    current_price: '42000',
                    high_24h: '42500',
                    low_24h: '41500',
                    volume_24h: '28000000000',
                    rsi: 60,
                },
            ];

            (executeQuery as jest.Mock).mockResolvedValue(mockData);

            const result = await getCurrentBitcoinMetrics();

            expect(result.rsi).toBe(0);
        });

        it('rejects current metrics when RSI is missing', async () => {
            const mockData = [
                {
                    current_price: '43500',
                    high_24h: '44000',
                    low_24h: '42000',
                    volume_24h: '30000000000',
                    rsi: null,
                },
                {
                    current_price: '42000',
                    high_24h: '42500',
                    low_24h: '41500',
                    volume_24h: '28000000000',
                    rsi: 60,
                },
            ];

            (executeQuery as jest.Mock).mockResolvedValue(mockData);

            await expect(getCurrentBitcoinMetrics()).rejects.toThrow();
        });

        it('should return current Bitcoin metrics with correct calculations', async () => {
            // Mock query response (matches the aliases in the query)
            const mockData = [
                {
                    current_price: '43500',
                    high_24h: '44000',
                    low_24h: '42000',
                    volume_24h: '30000000000',
                    rsi: '65',
                },
                {
                    current_price: '42000',
                    high_24h: '42500',
                    low_24h: '41500',
                    volume_24h: '28000000000',
                    rsi: '60',
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
        it('falls back to USD columns for an unknown runtime currency', async () => {
            (executeQuery as jest.Mock).mockResolvedValue([]);

            await getHistoricalPrices(30, undefined, undefined, 'GBP' as unknown as Currency);

            const [query] = (executeQuery as jest.Mock).mock.calls[0];

            expect(query).toMatch(/open_usd\s+AS\s+open/i);
            expect(query).not.toMatch(/open_gbp/i);
        });

        it('uses the stored CHF values for each historical date', async () => {
            const mockPrices = [
                {
                    date: '2024-01-01',
                    open: 90,
                    high: 100,
                    low: 80,
                    close: 95,
                    volume: 10,
                    rsi: 40,
                    rsi_status: 'Neutral',
                },
                {
                    date: '2024-01-02',
                    open: 110,
                    high: 120,
                    low: 100,
                    close: 115,
                    volume: 11,
                    rsi: 45,
                    rsi_status: 'Neutral',
                },
            ];

            (executeQuery as jest.Mock).mockResolvedValue(mockPrices);

            const result = await getHistoricalPrices(30, undefined, undefined, 'CHF');
            const [query] = (executeQuery as jest.Mock).mock.calls[0];

            expect(executeQuery).toHaveBeenCalledTimes(1);
            expect(query).toMatch(/open_chf\s+AS\s+open/i);
            expect(query).toMatch(/close_chf\s+AS\s+close/i);
            expect(result.map(price => price.close)).toEqual([95, 115]);
        });

        it('uses the real custom span to select monthly history', async () => {
            (executeQuery as jest.Mock).mockResolvedValue([]);

            await getHistoricalPrices(30, '2014-01-15', '2024-01-15', 'USD');

            const [query, parameters] = (executeQuery as jest.Mock).mock.calls[0];

            expect(query).toContain('dlh_gold__crypto_prices.agg_month_btc');
            expect(query).toMatch(/month_start_date\s+AS\s+date/i);
            expect(parameters).toEqual(['2014-01-15', '2024-01-15']);
        });

        it('uses the real custom span to keep short history daily', async () => {
            (executeQuery as jest.Mock).mockResolvedValue([]);

            await getHistoricalPrices(3650, '2024-01-01', '2024-01-31', 'USD');

            const [query] = (executeQuery as jest.Mock).mock.calls[0];

            expect(query).toContain('dlh_silver__crypto_prices.obt_fact_day_btc');
            expect(query).toMatch(/date_prices\s+AS\s+date/i);
        });

        it('preserves zero and exposes missing historical RSI as null', async () => {
            (executeQuery as jest.Mock).mockResolvedValue([
                {
                    date: '2024-01-01',
                    open: 90,
                    high: 100,
                    low: 80,
                    close: 95,
                    volume: 10,
                    rsi: 0,
                    rsi_status: 'Oversold',
                },
                {
                    date: '2024-01-02',
                    open: 110,
                    high: 120,
                    low: 100,
                    close: 115,
                    volume: 11,
                    rsi: null,
                    rsi_status: 'Neutral',
                },
            ]);

            const result = await getHistoricalPrices(30);

            expect(result.map(price => price.rsi)).toEqual([0, null]);
        });

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
        it('computes average price and total volume from daily source data', async () => {
            (executeQuery as jest.Mock).mockResolvedValue([]);

            await getAggregatedData('weekly');

            const [query] = (executeQuery as jest.Mock).mock.calls[0];

            expect(query).toMatch(/AVG\(daily\.close_usd\)/i);
            expect(query).toMatch(/SUM\(daily\.volume\)/i);
            expect(query).not.toMatch(/0\s+AS\s+"totalVolume"/i);
        });

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
                expect.stringContaining('dlh_gold__crypto_prices.agg_month_btc')
            );

            await getAggregatedData('quarterly');
            expect(executeQuery).toHaveBeenCalledWith(
                expect.stringContaining('dlh_gold__crypto_prices.agg_quarter_btc')
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

describe('PostgreSQL parameters', () => {
    it('passes date filters as positional values', async () => {
        (executeQuery as jest.Mock).mockResolvedValue([]);
        await getHistoricalPrices(30, '2023-01-01', '2023-01-31', 'USD');

        const lastCall = (executeQuery as jest.Mock).mock.calls[(executeQuery as jest.Mock).mock.calls.length - 1];

        expect(lastCall[0]).toContain('BETWEEN $1::date AND $2::date');
        expect(lastCall[1]).toEqual(['2023-01-01', '2023-01-31']);
    });

    it('passes the day count as a positional value', async () => {
        (executeQuery as jest.Mock).mockResolvedValue([]);
        await getHistoricalPrices(30, undefined, undefined, 'USD');

        const lastCall = (executeQuery as jest.Mock).mock.calls[(executeQuery as jest.Mock).mock.calls.length - 1];

        expect(lastCall[0]).toContain('CURRENT_DATE - $1::integer');
        expect(lastCall[1]).toEqual([30]);
    });
});
