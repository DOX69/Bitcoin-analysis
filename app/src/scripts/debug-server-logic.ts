
import dotenv from 'dotenv';
import path from 'path';

// Load env vars FIRST
const result = dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });
console.log('DOTENV RESULT:', result.parsed ? 'SUCCESS' : 'FAILED', result.error || '');
console.log('DIRECT ENV CHECK IN SCRIPT:', process.env.NEXT_PUBLIC_DATABRICKS_HOST);

// Now imports
import { env } from '../lib/env';

async function debugData() {
    console.log('--- DEBUG START ---');
    console.log('VERIFIED ENV HOST:', env.DATABRICKS_HOST);
    process.exit(0);
}

debugData();
