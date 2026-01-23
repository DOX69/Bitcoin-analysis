// Databricks SQL connection utilities
import { DBSQLClient } from '@databricks/sql';

interface DatabricksConfig {
    host: string;
    token: string;
    httpPath: string;
}

// Use inferred type from openSession() to avoid TypeScript compatibility issues
type DBSession = Awaited<ReturnType<Awaited<ReturnType<DBSQLClient['connect']>>['openSession']>>;

let client: DBSQLClient | null = null;
let session: DBSession | null = null;

/**
 * Initialize Databricks connection
 */
export async function initDatabricksConnection(config: DatabricksConfig): Promise<DBSession> {
    if (session) {
        return session;
    }

    try {
        client = new DBSQLClient();

        const connection = await client.connect({
            host: config.host,
            path: config.httpPath,
            token: config.token,
        });

        session = await connection.openSession();
        console.log('Databricks connection established');
        return session;
    } catch (error) {
        console.error('Failed to connect to Databricks:', error);
        throw error;
    }
}

/**
 * Execute a SQL query
 */
export async function executeQuery<T = any>(
    sql: string,
    config?: DatabricksConfig
): Promise<T[]> {
    try {
        // If no session exists and config is provided, initialize connection
        if (!session && config) {
            await initDatabricksConnection(config);
        }

        if (!session) {
            throw new Error('Databricks session not initialized');
        }

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

/**
 * Close Databricks connection
 */
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
        console.log('Databricks connection closed');
    } catch (error) {
        console.error('Failed to close Databricks connection:', error);
        throw error;
    }
}

/**
 * Get Databricks configuration from environment variables
 */
export function getDatabricksConfig(): DatabricksConfig {
    const host = process.env.DATABRICKS_HOST || process.env.NEXT_PUBLIC_DATABRICKS_HOST || '';
    const token = process.env.DATABRICKS_TOKEN || process.env.NEXT_PUBLIC_DATABRICKS_TOKEN || '';
    const httpPath = process.env.DATABRICKS_HTTP_PATH || process.env.NEXT_PUBLIC_DATABRICKS_HTTP_PATH || '';

    if (!host || !token || !httpPath) {
        console.warn('Databricks credentials not found in environment variables');
    }

    return {
        host,
        token,
        httpPath,
    };
}
