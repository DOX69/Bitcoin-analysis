
import dotenv from 'dotenv';
import path from 'path';

// Load env vars FIRST
const result = dotenv.config({ path: path.resolve(process.cwd(), '.env.local') });

// Now imports
import { env } from '../lib/env';

async function debugData() {
    process.exit(0);
}

debugData();
