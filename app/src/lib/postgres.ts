import { Pool, type QueryResultRow } from 'pg';
import { env } from './env';

interface PostgresPool {
    query(sql: string, parameters?: unknown[]): Promise<{ rows: QueryResultRow[] }>;
    end(): Promise<void>;
}

export function createPostgresAdapter(pool: PostgresPool) {
    return {
        async query<T extends QueryResultRow>(sql: string, parameters: unknown[] = []): Promise<T[]> {
            const result = await pool.query(sql, parameters);
            return result.rows as T[];
        },
        close(): Promise<void> {
            return pool.end();
        },
    };
}

const globalForPostgres = globalThis as typeof globalThis & {
    bitcoinAnalysisPool?: Pool;
};

function getPool(): Pool {
    if (!env.DATABASE_URL) {
        throw new Error('DATABASE_URL is required');
    }

    if (!globalForPostgres.bitcoinAnalysisPool) {
        globalForPostgres.bitcoinAnalysisPool = new Pool({
            connectionString: env.DATABASE_URL,
        });
    }

    return globalForPostgres.bitcoinAnalysisPool;
}

export function executeQuery<T extends QueryResultRow>(
    sql: string,
    parameters: unknown[] = []
): Promise<T[]> {
    return createPostgresAdapter(getPool()).query<T>(sql, parameters);
}
