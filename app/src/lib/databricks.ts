
import { DBSQLClient } from '@databricks/sql';
import { env } from '@/lib/env';

interface DatabricksConfig {
    host: string;
    token: string;
    httpPath: string;
}

type DBSession = Awaited<ReturnType<Awaited<ReturnType<DBSQLClient['connect']>>['openSession']>>;

let client: DBSQLClient | null = null;
let session: DBSession | null = null;

export async function initDatabricksConnection(): Promise<DBSession> {
    if (session) return session;

    if (!env.DATABRICKS_HOST || !env.DATABRICKS_PATH || !env.DATABRICKS_TOKEN) {
        const missing = [];
        if (!env.DATABRICKS_HOST) missing.push('DATABRICKS_HOST');
        if (!env.DATABRICKS_PATH) missing.push('DATABRICKS_PATH');
        if (!env.DATABRICKS_TOKEN) missing.push('DATABRICKS_TOKEN');
        throw new Error(`Databricks credentials missing in environment: ${missing.join(', ')}`);
    }

    try {
        client = new DBSQLClient();
        const connection = await client.connect({
            host: env.DATABRICKS_HOST.replace(/^https?:\/\//, ''),
            path: env.DATABRICKS_PATH,
            token: env.DATABRICKS_TOKEN,
        });

        session = await connection.openSession();
        return session;
    } catch (error) {
        console.error('Failed to connect to Databricks:', error);
        throw error;
    }
}

export async function executeQuery<T = any>(sql: string): Promise<T[]> {
    try {
        if (!session) {
            await initDatabricksConnection();
        }

        if (!session) throw new Error('Session initialization failed');

        const queryOperation = await session.executeStatement(sql, {
            runAsync: true,
            maxRows: 10000,
        });

        const result = await queryOperation.fetchAll();
        await queryOperation.close();

        return result as T[];
    } catch (error) {
        console.error('Query execution failed:', error);
        throw error;
    }
}

export async function closeDatabricksConnection(): Promise<void> {
    try {
        if (session) {
            await session.close();
            session = null;
        }
        if (client) {
            await client.close();
            client = null;
        }
    } catch (error) {
        console.error('Failed to close Databricks connection:', error);
        throw error;
    }
}

export function getDatabricksConfig(): DatabricksConfig {
    return {
        host: env.DATABRICKS_HOST,
        token: env.DATABRICKS_TOKEN,
        httpPath: env.DATABRICKS_PATH,
    };
}
