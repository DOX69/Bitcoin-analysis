import fs from 'node:fs';
import path from 'node:path';
import { BitcoinSearchParamsSchema } from '@/lib/schemas';

const SRC_ROOT = path.resolve(process.cwd(), 'src');
const APP_ROOT = path.resolve(process.cwd());

function getProductionSources(directory: string): string[] {
    return fs.readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
        if (entry.name.endsWith('.disabled')) {
            return [];
        }

        const entryPath = path.join(directory, entry.name);
        if (entry.isDirectory()) {
            return entry.name === '__tests__' ? [] : getProductionSources(entryPath);
        }
        return /\.(ts|tsx)$/.test(entry.name) ? [entryPath] : [];
    });
}

describe('forecast removal', () => {
    it('rejects forecast API requests', () => {
        expect(BitcoinSearchParamsSchema.safeParse({ type: 'forecast' }).success).toBe(false);
    });

    it('leaves no forecast implementation in production sources', () => {
        const matches = getProductionSources(SRC_ROOT).filter(file =>
            /forecast|forcast_btc_price/i.test(fs.readFileSync(file, 'utf8'))
        );

        expect(matches).toEqual([]);
        expect(fs.existsSync(path.join(SRC_ROOT, 'lib', 'forecast-utils.ts'))).toBe(false);
    });
});
describe('landing truth', () => {
    const landingSurfaces = [
        path.join(SRC_ROOT, 'app', 'layout.tsx'),
        path.join(SRC_ROOT, 'components', 'landing', 'Hero.tsx'),
        path.join(SRC_ROOT, 'components', 'landing', 'Features.tsx'),
        path.join(SRC_ROOT, 'components', 'landing', 'Footer.tsx'),
    ];

    it('makes no unsupported product claims', () => {
        const unsupportedClaim =
            /forecast|neural networks?|machine learning|\bpredict(?:s|ed|ion|ive)?\b|AI-Powered|real[- ]time|\blive (?:data|prices?|analytics)|portfolio/i;
        const matches = landingSurfaces.filter(file =>
            unsupportedClaim.test(fs.readFileSync(file, 'utf8'))
        );

        expect(matches).toEqual([]);
    });

    it('states the daily PostgreSQL update and Railway hosting accurately', () => {
        const content = landingSurfaces
            .map(file => fs.readFileSync(file, 'utf8'))
            .join('\n');

        expect(content).toMatch(/updated daily/i);
        expect(content).toMatch(/PostgreSQL/i);
        expect(content).toMatch(/hosted on Railway/i);
    });
});

describe('Databricks adapter removal', () => {
    it('leaves no Databricks, Delta, or Vercel text in production sources', () => {
        const matches = getProductionSources(SRC_ROOT).filter(file =>
            /databricks|delta|vercel/i.test(fs.readFileSync(file, 'utf8'))
        );

        expect(matches).toEqual([]);
    });

    it('leaves no Databricks driver or browser credential fallback in production sources', () => {
        const matches = getProductionSources(SRC_ROOT).filter(file =>
            /@databricks\/sql|NEXT_PUBLIC_DATABRICKS/.test(fs.readFileSync(file, 'utf8'))
        );

        expect(matches).toEqual([]);
        expect(fs.existsSync(path.join(SRC_ROOT, 'lib', 'databricks.ts'))).toBe(false);
    });

    it('leaves no Databricks or dotenv runtime dependency, wrapper, or config', () => {
        const packageJson = JSON.parse(fs.readFileSync(path.join(APP_ROOT, 'package.json'), 'utf8'));
        const inspectedFiles = [
            'package.json',
            'package-lock.json',
            'next.config.ts',
            'jest.setup.ts',
            'jest.config.ts',
            'playwright-verify.js',
        ].map(file => path.join(APP_ROOT, file));
        const matches = inspectedFiles.filter(file =>
            /@databricks\/sql|NEXT_PUBLIC_DATABRICKS|DATABRICKS_(?:HOST|TOKEN|PATH|HTTP_PATH|CATALOG)|forecast|dotenv|\.env(?:\.local)?/i.test(
                fs.readFileSync(file, 'utf8')
            )
        );

        expect(matches).toEqual([]);
        expect(packageJson.scripts).toMatchObject({
            dev: 'next dev',
            build: 'next build',
            start: 'next start',
        });
        expect(packageJson.dependencies?.['@databricks/sql']).toBeUndefined();
        expect(packageJson.devDependencies?.dotenv).toBeUndefined();
        expect(fs.existsSync(path.join(APP_ROOT, 'debug-db.js'))).toBe(false);
        expect(fs.existsSync(path.join(APP_ROOT, 'scripts', 'run-with-catalog.js'))).toBe(false);
        expect(fs.existsSync(path.join(SRC_ROOT, 'scripts', 'debug-server-logic.ts'))).toBe(false);
    });

    it('keeps DATABASE_URL server-only', () => {
        const runtimeFiles = [
            ...getProductionSources(SRC_ROOT),
            path.join(APP_ROOT, 'next.config.ts'),
            path.join(APP_ROOT, 'package.json'),
        ];
        const publicMatches = runtimeFiles.filter(file =>
            /NEXT_PUBLIC_DATABASE_URL/.test(fs.readFileSync(file, 'utf8'))
        );

        expect(publicMatches).toEqual([]);
    });
});
