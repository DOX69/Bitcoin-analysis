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

        it('should resolve @/lib/postgres', () => {
            process.env.DATABASE_URL = 'postgresql://test:test@localhost:5432/test';
            const importModule = () => require('@/lib/postgres');
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

    describe('@/lib/postgres exports', () => {
        it('should export executeQuery function', () => {
            const { executeQuery } = require('@/lib/postgres');
            expect(typeof executeQuery).toBe('function');
        });

        it('should export createPostgresAdapter function', () => {
            const { createPostgresAdapter } = require('@/lib/postgres');
            expect(typeof createPostgresAdapter).toBe('function');
        });
    });
});
