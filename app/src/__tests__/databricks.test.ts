/**
 * Unit tests for Databricks connection utilities
 */

import {
    getDatabricksConfig,
} from '@/lib/databricks';

// Mock the env module
jest.mock('@/lib/env', () => ({
    env: {
        DATABRICKS_HOST: 'https://mock.databricks.com',
        DATABRICKS_TOKEN: 'mock-token',
        DATABRICKS_PATH: '/sql/mock',
    },
}));

describe('Databricks Utilities', () => {
    describe('getDatabricksConfig', () => {
        it('should return configuration from env module', () => {
            const config = getDatabricksConfig();

            expect(config).toEqual({
                host: 'https://mock.databricks.com',
                token: 'mock-token',
                httpPath: '/sql/mock',
            });
        });
    });
});

