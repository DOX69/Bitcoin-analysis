import type { Config } from 'jest';
import nextJest from 'next/jest.js';

const createJestConfig = nextJest({
    // Point next/jest at the app root.
    dir: './',
});

// Add any custom config to be passed to Jest
const config: Config = {
    coverageProvider: 'v8',
    testEnvironment: 'jsdom',
    setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
    moduleNameMapper: {
        '^@/(.*)$': '<rootDir>/src/$1',
        '^jose$': '<rootDir>/node_modules/jose/dist/node/cjs/index.js',
        '^jose/(.*)$': '<rootDir>/node_modules/jose/dist/node/cjs/$1',
    },
    testMatch: [
        '**/__tests__/**/*.test.ts',
        '**/__tests__/**/*.test.tsx',
    ],
    transformIgnorePatterns: [
        '/node_modules/(?!(jose|openid-client)/)',
    ],
};

// createJestConfig is exported this way to ensure that next/jest can load the Next.js config which is async
export default createJestConfig(config);
