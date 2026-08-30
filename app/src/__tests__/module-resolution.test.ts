/**
 * Module Resolution Tests
 * 
 * These tests verify that all path aliases (@/*) resolve correctly.
 * This prevents deployment failures due to module resolution errors.
 * 
 * IMPORTANT: Do not modify or remove these tests. They serve as a safety net
 * to catch module resolution issues before deployment.
 */

import * as bitcoinApi from '@/lib/bitcoin-api';
import * as bitcoinDataServer from '@/lib/bitcoin-data-server';
import * as postgres from '@/lib/postgres';

describe('Module Resolution - Path Aliases', () => {
    describe('@/lib modules', () => {
        it('should resolve @/lib/bitcoin-data-server', () => {
            expect(bitcoinDataServer).toBeDefined();
        });

        it('should resolve @/lib/bitcoin-api', () => {
            expect(bitcoinApi).toBeDefined();
        });

        it('should resolve @/lib/postgres', () => {
            process.env.DATABASE_URL = 'postgresql://test:test@localhost:5432/test';
            expect(postgres).toBeDefined();
        });
    });

    describe('@/lib/bitcoin-data-server exports', () => {
        it('should export getCurrentBitcoinMetrics function', () => {
            expect(typeof bitcoinDataServer.getCurrentBitcoinMetrics).toBe('function');
        });

        it('should export getHistoricalPrices function', () => {
            expect(typeof bitcoinDataServer.getHistoricalPrices).toBe('function');
        });

        it('should export getAggregatedData function', () => {
            expect(typeof bitcoinDataServer.getAggregatedData).toBe('function');
        });
    });

    describe('@/lib/bitcoin-api exports', () => {
        it('should export getCurrentBitcoinMetrics function', () => {
            expect(typeof bitcoinApi.getCurrentBitcoinMetrics).toBe('function');
        });

        it('should export getHistoricalPrices function', () => {
            expect(typeof bitcoinApi.getHistoricalPrices).toBe('function');
        });

        it('should export getAggregatedData function', () => {
            expect(typeof bitcoinApi.getAggregatedData).toBe('function');
        });
    });

    describe('@/lib/postgres exports', () => {
        it('should export executeQuery function', () => {
            expect(typeof postgres.executeQuery).toBe('function');
        });

        it('should export createPostgresAdapter function', () => {
            expect(typeof postgres.createPostgresAdapter).toBe('function');
        });
    });
});
