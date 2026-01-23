/**
 * Module Resolution Tests
 * 
 * These tests verify that all path aliases (@/*) resolve correctly.
 * This prevents Vercel build failures due to module resolution errors.
 * 
 * IMPORTANT: Do not modify or remove these tests. They serve as a safety net
 * to catch module resolution issues before deployment.
 */

describe('Module Resolution - Path Aliases', () => {
    describe('@/lib modules', () => {
        it('should resolve @/lib/bitcoin-data-server', () => {
            // This test verifies the module can be imported without errors
            const importModule = () => require('@/lib/bitcoin-data-server');
            expect(importModule).not.toThrow();
        });

        it('should resolve @/lib/bitcoin-api', () => {
            const importModule = () => require('@/lib/bitcoin-api');
            expect(importModule).not.toThrow();
        });

        it('should resolve @/lib/databricks', () => {
            const importModule = () => require('@/lib/databricks');
            expect(importModule).not.toThrow();
        });
    });

    describe('@/lib/bitcoin-data-server exports', () => {
        it('should export getCurrentBitcoinMetrics function', () => {
            const { getCurrentBitcoinMetrics } = require('@/lib/bitcoin-data-server');
            expect(typeof getCurrentBitcoinMetrics).toBe('function');
        });

        it('should export getHistoricalPrices function', () => {
            const { getHistoricalPrices } = require('@/lib/bitcoin-data-server');
            expect(typeof getHistoricalPrices).toBe('function');
        });

        it('should export getAggregatedData function', () => {
            const { getAggregatedData } = require('@/lib/bitcoin-data-server');
            expect(typeof getAggregatedData).toBe('function');
        });
    });

    describe('@/lib/bitcoin-api exports', () => {
        it('should export getCurrentBitcoinMetrics function', () => {
            const { getCurrentBitcoinMetrics } = require('@/lib/bitcoin-api');
            expect(typeof getCurrentBitcoinMetrics).toBe('function');
        });

        it('should export getHistoricalPrices function', () => {
            const { getHistoricalPrices } = require('@/lib/bitcoin-api');
            expect(typeof getHistoricalPrices).toBe('function');
        });

        it('should export getAggregatedData function', () => {
            const { getAggregatedData } = require('@/lib/bitcoin-api');
            expect(typeof getAggregatedData).toBe('function');
        });
    });

    describe('@/lib/databricks exports', () => {
        it('should export executeQuery function', () => {
            const { executeQuery } = require('@/lib/databricks');
            expect(typeof executeQuery).toBe('function');
        });

        it('should export getDatabricksConfig function', () => {
            const { getDatabricksConfig } = require('@/lib/databricks');
            expect(typeof getDatabricksConfig).toBe('function');
        });

        it('should export initDatabricksConnection function', () => {
            const { initDatabricksConnection } = require('@/lib/databricks');
            expect(typeof initDatabricksConnection).toBe('function');
        });

        it('should export closeDatabricksConnection function', () => {
            const { closeDatabricksConnection } = require('@/lib/databricks');
            expect(typeof closeDatabricksConnection).toBe('function');
        });
    });
});
