const { DBSQLClient } = require('@databricks/sql');
const fs = require('fs');
const path = require('path');

// Load .env.local manually
const envPath = path.join(__dirname, '.env.local');
const envContent = fs.readFileSync(envPath, 'utf8');
const env = {};
envContent.split('\n').forEach(line => {
    const [key, value] = line.split('=');
    if (key && value) {
        env[key.trim()] = value.trim();
    }
});

const host = env['DATABRICKS_HOST'] || env['NEXT_PUBLIC_DATABRICKS_HOST'];
const token = env['DATABRICKS_TOKEN'] || env['NEXT_PUBLIC_DATABRICKS_TOKEN'];
const httpPath = env['DATABRICKS_HTTP_PATH'] || env['NEXT_PUBLIC_DATABRICKS_HTTP_PATH'];

const client = new DBSQLClient();

async function run() {
    try {
        await client.connect({
            host: host,
            path: httpPath,
            token: token
        });

        const session = await client.openSession();

        const query = "SELECT * FROM prod.dlh_silver__crypto_prices.obt_fact_day_btc LIMIT 1";

        const result = await session.executeStatement(query, { runAsync: true });
        const data = await result.fetchAll();

        await session.close();
        await client.close();
    } catch (error) {
        console.error('ERROR:', error);
    }
}

run();
