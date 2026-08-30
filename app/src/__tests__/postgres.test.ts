import type { QueryResultRow } from 'pg';

const query = jest.fn();
const end = jest.fn();
const Pool = jest.fn(() => ({ query, end }));

jest.mock('pg', () => ({ Pool }));

describe('PostgreSQL adapter', () => {
    beforeAll(() => {
        process.env.DATABASE_URL = 'postgresql://user:password@localhost:5432/bitcoin';
    });

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('reuses one pool and returns query rows', async () => {
        query
            .mockResolvedValueOnce({ rows: [{ value: 1 }] })
            .mockResolvedValueOnce({ rows: [{ value: 2 }] });
        const { executeQuery } = await import('@/lib/postgres');

        await expect(executeQuery<{ value: number }>('SELECT $1::integer AS value', [1]))
            .resolves.toEqual([{ value: 1 }]);
        await expect(executeQuery<{ value: number }>('SELECT $1::integer AS value', [2]))
            .resolves.toEqual([{ value: 2 }]);

        expect(Pool).toHaveBeenCalledTimes(1);
        expect(Pool).toHaveBeenCalledWith({
            connectionString: 'postgresql://user:password@localhost:5432/bitcoin',
        });
        expect(query).toHaveBeenNthCalledWith(1, 'SELECT $1::integer AS value', [1]);
        expect(query).toHaveBeenNthCalledWith(2, 'SELECT $1::integer AS value', [2]);
    });

    it('closes an adapter through its normal lifecycle API', async () => {
        const pool = {
            query: jest.fn().mockResolvedValue({ rows: [] as QueryResultRow[] }),
            end: jest.fn().mockResolvedValue(undefined),
        };
        const { createPostgresAdapter } = await import('@/lib/postgres');
        const adapter = createPostgresAdapter(pool);

        await adapter.close();

        expect(pool.end).toHaveBeenCalledTimes(1);
    });
});
