#!/usr/bin/env tsx
/**
 * Comprehensive test script for Databricks warehouse connection
 * Tests all silver and gold tables used by the web app
 */

import dotenv from 'dotenv';
import path from 'path';

// Load environment variables from .env.local
dotenv.config({ path: path.resolve(__dirname, '../../.env.local') });

import { initDatabricksConnection, executeQuery, closeDatabricksConnection, getDatabricksConfig } from '../lib/databricks';

interface TestResult {
    tableName: string;
    success: boolean;
    error?: string;
    rowCount?: number;
    sampleData?: any[];
    columns?: string[];
}

const TABLES_TO_TEST = [
    {
        name: 'Silver - BTC Daily Facts',
        fullName: 'prod.dlh_silver__crypto_prices.obt_fact_day_btc',
        query: 'SELECT * FROM prod.dlh_silver__crypto_prices.obt_fact_day_btc ORDER BY date_prices DESC LIMIT 5'
    },
    {
        name: 'Gold - BTC Weekly Aggregation',
        fullName: 'prod.dlh_gold__crypto_prices.agg_week_btc',
        query: 'SELECT * FROM prod.dlh_gold__crypto_prices.agg_week_btc ORDER BY iso_week_start_date DESC LIMIT 5'
    },
    {
        name: 'Gold - BTC Monthly Aggregation',
        fullName: 'prod.dlh_gold__crypto_prices.agg_month_btc',
        query: 'SELECT * FROM prod.dlh_gold__crypto_prices.agg_month_btc ORDER BY month_start_date DESC LIMIT 5'
    },
    {
        name: 'Gold - BTC Quarterly Aggregation',
        fullName: 'prod.dlh_gold__crypto_prices.agg_quarter_btc',
        query: 'SELECT * FROM prod.dlh_gold__crypto_prices.agg_quarter_btc ORDER BY quarter_start_date DESC LIMIT 5'
    }
];

async function testTable(tableName: string, fullName: string, query: string): Promise<TestResult> {
    try {
        const results = await executeQuery(query);

        // Get column names from first row
        const columns = results.length > 0 ? Object.keys(results[0]) : [];

        return {
            tableName,
            success: true,
            rowCount: results.length,
            sampleData: results,
            columns
        };
    } catch (error: any) {
        console.error(`   ❌ Failed: ${error.message}`);
        return {
            tableName,
            success: false,
            error: error.message
        };
    }
}

async function main() {
    const config = getDatabricksConfig();

    // Validate config
    if (!config.host || !config.token || !config.httpPath) {
        console.error('❌ Missing Databricks configuration!');
        console.error('Please ensure environment variables are set:');
        console.error('  - NEXT_PUBLIC_DATABRICKS_HOST');
        console.error('  - NEXT_PUBLIC_DATABRICKS_TOKEN');
        console.error('  - NEXT_PUBLIC_DATABRICKS_HTTP_PATH');
        process.exit(1);
    }

    try {
        // Initialize connection
        await initDatabricksConnection();

        // Test each table
        const results: TestResult[] = [];
        for (const table of TABLES_TO_TEST) {
            const result = await testTable(table.name, table.fullName, table.query);
            results.push(result);
        }

        // Summary
        const failed = results.filter(r => !r.success).length;

        if (failed > 0) {
            console.error('\n❌ Failed Tables:');
            results.filter(r => !r.success).forEach(r => {
                console.error(`   - ${r.tableName}: ${r.error}`);
            });
        }

        if (failed > 0) {
            console.error('\n⚠️  Some tables failed to connect. Please check the errors above.');
            process.exit(1);
        }

    } catch (error: any) {
        console.error('\n❌ Connection test failed:', error.message);
        process.exit(1);
    } finally {
        // Clean up
        await closeDatabricksConnection();
    }
}

// Run the tests
main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
});
