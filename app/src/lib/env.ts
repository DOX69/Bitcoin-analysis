import { z } from 'zod';

const envSchema = z.object({
    DATABASE_URL: z.string().min(1).optional(),
    NODE_ENV: z.string().default('development'),
});

export const env = envSchema.parse({
    DATABASE_URL: process.env.DATABASE_URL,
    NODE_ENV: process.env.NODE_ENV || 'development',
});
