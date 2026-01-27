/**
 * Unit tests for Forecast implementation (Server & Client logic)
 */

import {
    getForecastData,
    convertPrice,
    getCurrencyRates,
} from '@/lib/bitcoin-data-server';
import { getForecastSlice } from '@/lib/forecast-utils';
import { BitcoinForecastSchema } from '@/lib/schemas';

// Mock the databricks module
jest.mock('@/lib/databricks', () => ({
    executeQuery: jest.fn(),
}));

import { executeQuery } from '@/lib/databricks';

describe('Forecast Implementation Tests', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        // Suppress console.error during tests
        jest.spyOn(console, 'error').mockImplementation(() => { });
    });

    afterEach(() => {
        jest.restoreAllMocks();
    });

    // ------------------------------------------------------------------------
    // Server-Side Tests: getForecastData & Currency Conversion
    // ------------------------------------------------------------------------
    describe('getForecastData (Server Side)', () => {
        const generateMockData = (count: number) => Array.from({ length: count }, (_, i) => {
            const date = new Date('2025-01-01T00:00:00Z');
            date.setUTCDate(date.getUTCDate() + i);
            return {
                date_prices: date.toISOString().split('T')[0],
                predicted_close_usd: 50000 + i,
                predicted_close_usd_lower: 49000 + i,
                predicted_close_usd_upper: 51000 + i,
                predicted_at: '2025-01-01',
            };
        });

        const mockForecastData = generateMockData(400);

        it('should fetch forecast data and parse it correctly for USD (Default)', async () => {
            (executeQuery as jest.Mock).mockResolvedValue(mockForecastData.slice(0, 365));

            const result = await getForecastData('USD');

            // Verify query execution (cannot easily verify LIMIT in SQL string here without strict string matching)
            expect(executeQuery).toHaveBeenCalled();
            expect(result.length).toBe(365);
            expect(result[0].predicted_close_usd).toBe(50000);
        });

        it('should convert forecast data to EUR when requested', async () => {
            // Mock getForecastData query result
            (executeQuery as jest.Mock)
                .mockResolvedValueOnce(mockForecastData.slice(0, 10)) // First call: getForecastData
                .mockResolvedValueOnce([{ rate_usd_chf: 0.9, rate_usd_eur: 0.85 }]); // Second call: getCurrencyRates

            const result = await getForecastData('EUR');

            // 50000 * 0.85 = 42500
            expect(result[0].predicted_close_usd).toBe(42500);
            expect(result[0].predicted_close_usd_lower).toBe(41650); // 49000 * 0.85
        });

        it('should convert forecast data to CHF when requested', async () => {
            // Mock getForecastData query result
            (executeQuery as jest.Mock)
                .mockResolvedValueOnce(mockForecastData.slice(0, 10))
                .mockResolvedValueOnce([{ rate_usd_chf: 0.90, rate_usd_eur: 0.85 }]);

            const result = await getForecastData('CHF');

            // 50000 * 0.90 = 45000
            expect(result[0].predicted_close_usd).toBe(45000);
        });

        it('should deduplicate forecast data by date', async () => {
            const duplicateData = [
                { date_prices: '2025-01-01', predicted_close_usd: 100, predicted_close_usd_lower: 90, predicted_close_usd_upper: 110, predicted_at: '2025-01-01' },
                { date_prices: '2025-01-01', predicted_close_usd: 200, predicted_close_usd_lower: 190, predicted_close_usd_upper: 210, predicted_at: '2025-01-01' }, // Duplicate
                { date_prices: '2025-01-02', predicted_close_usd: 300, predicted_close_usd_lower: 290, predicted_close_usd_upper: 310, predicted_at: '2025-01-01' },
            ];

            (executeQuery as jest.Mock).mockResolvedValue(duplicateData);

            const result = await getForecastData('USD');

            expect(result).toHaveLength(2); // Should be 2 unique dates
            expect(result[0].predicted_close_usd).toBe(100); // Keeps the first one
            expect(result[1].predicted_close_usd).toBe(300);
        });
    });

    describe('convertPrice Utility', () => {
        const rates = { USD_CHF: 0.90, USD_EUR: 0.85 };

        it('should return USD price as is', () => {
            expect(convertPrice(100, 'USD', rates)).toBe(100);
        });

        it('should convert to CHF', () => {
            expect(convertPrice(100, 'CHF', rates)).toBe(90);
        });

        it('should convert to EUR', () => {
            expect(convertPrice(100, 'EUR', rates)).toBe(85);
        });
    });

    // ------------------------------------------------------------------------
    // Client-Side Tests: getForecastSlice (Aggregation)
    // ------------------------------------------------------------------------
    describe('getForecastSlice (Client Side)', () => {
        const generateData = (days: number) => Array.from({ length: days }, (_, i) => {
            const date = new Date('2025-01-01');
            date.setDate(date.getDate() + i);
            return {
                date_prices: date.toISOString(),
                predicted_close_usd: 100 + i,
                predicted_close_usd_lower: 90 + i,
                predicted_close_usd_upper: 110 + i,
                predicted_at: '2025-01-01',
            };
        });

        const oneYearData = generateData(365);

        it('should return 7 days for 1w filter', () => {
            const result = getForecastSlice(oneYearData, '1w');
            expect(result).toHaveLength(7);
        });

        it('should return 30 days for 1m filter', () => {
            const result = getForecastSlice(oneYearData, '1m');
            expect(result).toHaveLength(30);
        });

        it('should return 180 days for 6m filter', () => {
            const result = getForecastSlice(oneYearData, '6m');
            expect(result).toHaveLength(180);
        });

        it('should return 365 days for 1y and ytd filter', () => {
            expect(getForecastSlice(oneYearData, '1y')).toHaveLength(365);
            expect(getForecastSlice(oneYearData, 'ytd')).toHaveLength(365);
        });

        it('should aggregate data monthly for ALL filter', () => {
            // Data spans 1 year (Jan 2025 - Dec 2025)
            // 365 days -> Should return 12-13 points (Start of each month)
            const result = getForecastSlice(oneYearData, 'all');

            // Check that we have approx 12-13 items
            expect(result.length).toBeGreaterThanOrEqual(12);
            expect(result.length).toBeLessThanOrEqual(13);

            // Check that consecutive items are in different months
            for (let i = 1; i < result.length; i++) {
                const prevDate = new Date(result[i - 1].date_prices);
                const currDate = new Date(result[i].date_prices);
                expect(prevDate.getMonth()).not.toBe(currDate.getMonth());
            }
        });

        it('should return empty array if input is empty', () => {
            expect(getForecastSlice([], 'all')).toEqual([]);
        });
    });
});
