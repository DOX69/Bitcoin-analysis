/**
 * Unit tests for Databricks connection utilities
 */

import {
    getDatabricksConfig,
} from '@/lib/databricks';

describe('Databricks Utilities', () => {
    describe('getDatabricksConfig', () => {
        it('should read configuration from environment variables', () => {
            const config = getDatabricksConfig();

            expect(config).toMatchObject({
                host: expect.any(String),
                token: expect.any(String),
                httpPath: expect.any(String),
            });
        });

        it('should prioritize server-side environment variables', () => {
            process.env.NEXT_PUBLIC_DATABRICKS_HOST = 'https://custom.databricks.com';
            process.env.DATABRICKS_HOST = 'https://old.databricks.com';

            const config = getDatabricksConfig();

            expect(config.host).toBe('https://old.databricks.com');
        });

        it('should handle missing environment variables gracefully', () => {
            const originalHost = process.env.NEXT_PUBLIC_DATABRICKS_HOST;
            const originalToken = process.env.NEXT_PUBLIC_DATABRICKS_TOKEN;
            const originalPath = process.env.NEXT_PUBLIC_DATABRICKS_HTTP_PATH;

            delete process.env.NEXT_PUBLIC_DATABRICKS_HOST;
            delete process.env.NEXT_PUBLIC_DATABRICKS_TOKEN;
            delete process.env.NEXT_PUBLIC_DATABRICKS_HTTP_PATH;
            delete process.env.DATABRICKS_HOST;
            delete process.env.DATABRICKS_TOKEN;
            delete process.env.DATABRICKS_HTTP_PATH;

            const config = getDatabricksConfig();

            expect(config).toMatchObject({
                host: '',
                token: '',
                httpPath: '',
            });

            // Restore environment variables
            process.env.NEXT_PUBLIC_DATABRICKS_HOST = originalHost;
            process.env.NEXT_PUBLIC_DATABRICKS_TOKEN = originalToken;
            process.env.NEXT_PUBLIC_DATABRICKS_HTTP_PATH = originalPath;
        });
    });
});
