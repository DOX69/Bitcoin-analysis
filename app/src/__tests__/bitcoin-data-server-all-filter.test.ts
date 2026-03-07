
import {
    getHistoricalPrices,
} from '@/lib/bitcoin-data-server';
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

// Mock env
jest.mock('@/lib/env', () => ({
    env: {
        DATABRICKS_HOST: 'https://test.databricks.com',
    },
}));

describe('Bitcoin API - All Filter Logic', () => {
    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('should use monthly aggregated table when days >= 1800 (ALL filter)', async () => {
        const mockPrices = [
            {
                date: '2024-01-01',
                open: 40000,
                high: 41000,
                low: 39000,
                close: 40500,
                volume: 0,
                rsi: 50,
                rsi_status: 'Neutral',
            },
        ];

        (executeQuery as jest.Mock).mockResolvedValue(mockPrices);

        // Act: Request 10 years of data (simulating 'All' filter)
        await getHistoricalPrices(3650);

        // Assert: Verify the correct table is queried
        expect(executeQuery).toHaveBeenCalledWith(
            expect.stringContaining('prod.dlh_gold__crypto_prices.agg_month_btc'),
            expect.objectContaining({ days: -3650 })
        );
        expect(executeQuery).toHaveBeenCalledWith(
            expect.stringContaining('CASE'), // Checks for the RSI status case statement
            expect.any(Object)
        );
        expect(executeQuery).toHaveBeenCalledWith(
            expect.stringContaining("month_start_date as date"),
            expect.any(Object)
        );
    });

    it('should use daily table when days < 1800', async () => {
        const mockPrices = [
            {
                date: '2024-01-01',
                open: 40000,
                high: 41000,
                low: 39000,
                close: 40500,
                volume: 1000,
                rsi: 50,
                rsi_status: 'Neutral',
            },
        ];

        (executeQuery as jest.Mock).mockResolvedValue(mockPrices);

        // Act: Request 30 days of data
        await getHistoricalPrices(30);

        // Assert: Verify the correct table is queried
        expect(executeQuery).toHaveBeenCalledWith(
            expect.stringContaining('prod.dlh_silver__crypto_prices.obt_fact_day_btc'),
            expect.objectContaining({ days: -30 })
        );

        // Ensure agg_month_btc is NEVER queried
        const aggMonthCalls = (executeQuery as jest.Mock).mock.calls.filter(call =>
            call[0].includes('agg_month_btc')
        );
        expect(aggMonthCalls).toHaveLength(0);
    });
});
