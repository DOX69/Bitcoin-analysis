/**
 * Unit tests for Technical Indicators (MACD, SMA, EMA)
 * Following TDD methodology: Phase 2 RED/GREEN Fix
 */

import {
    getHistoricalPrices,
} from '@/lib/bitcoin-data-server';
import { BitcoinHistorySchema } from '@/lib/schemas';

// Mock the databricks module
jest.mock('@/lib/databricks', () => ({
    executeQuery: jest.fn(),
}));

import { executeQuery } from '@/lib/databricks';

describe('Technical Indicators Data Fetching', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    const mockDataWithIndicators = [
        {
            date: '2026-03-01',
            open: 60000,
            high: 61000,
            low: 59000,
            close: 60500,
            volume: 1000,
            rsi: 55,
            rsi_status: 'Neutral',
            // Aliased indicator columns (as they would return from SQL)
            macd: 150,
            macd_signal: 120,
            macd_hist: 30,
            sma_7: 60100,
            sma_50: 58000,
            sma_200: 50000,
            ema_7: 60200,
            ema_50: 58500,
            ema_200: 51000
        }
    ];

    it('should include indicator data in historical prices response', async () => {
        (executeQuery as jest.Mock).mockResolvedValue(mockDataWithIndicators);

        const result = await getHistoricalPrices(30, undefined, undefined, 'USD');

        expect(result[0]).toMatchObject({
            macd: 150,
            macd_signal: 120,
            macd_hist: 30,
            sma_7: 60100,
            sma_50: 58000,
            sma_200: 50000,
            ema_7: 60200,
            ema_50: 58500,
            ema_200: 51000
        });
    });

    it('should convert indicators to CHF', async () => {
        const mockRatesData = [{ rate_usd_chf: 0.90, rate_usd_eur: 0.85 }];

        // Mock executeQuery to handle both the rates fetch (getCurrencyRates) 
        // and the prices fetch (getHistoricalPrices)
        (executeQuery as jest.Mock)
            .mockResolvedValueOnce(mockRatesData) // Call from getCurrencyRates
            .mockResolvedValueOnce(mockDataWithIndicators); // Call from getHistoricalPrices

        const result = await getHistoricalPrices(30, undefined, undefined, 'CHF');

        expect(result[0].sma_7).toBeCloseTo(60100 * 0.9, 0);
        expect(result[0].ema_50).toBeCloseTo(58500 * 0.9, 0);
    });

    it('should include technical indicators in monthly aggregation ("ALL" timeframe)', async () => {
        (executeQuery as jest.Mock).mockResolvedValue(mockDataWithIndicators);

        // timeframe > 1800 triggers monthly aggregation
        const result = await getHistoricalPrices(2000, undefined, undefined, 'USD');

        expect(result[0]).toHaveProperty('macd');
        expect(result[0]).toHaveProperty('sma_7');
        expect(result[0].sma_7).toBe(60100);
    });
});
