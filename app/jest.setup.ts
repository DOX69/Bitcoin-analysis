import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

global.TextEncoder = TextEncoder;
Object.defineProperty(global, 'TextDecoder', {
    configurable: true,
    value: TextDecoder,
});
