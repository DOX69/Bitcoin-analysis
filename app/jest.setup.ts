import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as any;

// Mock environment variables for testing
process.env.NEXT_PUBLIC_DATABRICKS_HOST = 'https://test.databricks.com';
process.env.NEXT_PUBLIC_DATABRICKS_TOKEN = 'test-token';
process.env.NEXT_PUBLIC_DATABRICKS_HTTP_PATH = '/sql/1.0/warehouses/test';
