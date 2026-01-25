import { z } from 'zod';

const envSchema = z.object({
    DATABRICKS_HOST: z.string().default(''),
    DATABRICKS_PATH: z.string().default(''),
    DATABRICKS_TOKEN: z.string().default(''),
    NODE_ENV: z.string().default('development'),
});

const _env = envSchema.safeParse({
    DATABRICKS_HOST: process.env.DATABRICKS_HOST || process.env.NEXT_PUBLIC_DATABRICKS_HOST,
    DATABRICKS_PATH: process.env.DATABRICKS_PATH || process.env.NEXT_PUBLIC_DATABRICKS_HTTP_PATH,
    DATABRICKS_TOKEN: process.env.DATABRICKS_TOKEN || process.env.NEXT_PUBLIC_DATABRICKS_TOKEN,
    NODE_ENV: process.env.NODE_ENV || 'development',
});

export const env = _env.success ? _env.data : {
    DATABRICKS_HOST: '',
    DATABRICKS_PATH: '',
    DATABRICKS_TOKEN: '',
    NODE_ENV: 'development',
};

if (!_env.success) {
    console.warn('⚠️ Databricks environment variables missing or invalid. Check your .env.local file.');
}
