import { AggregatedDataSchema, BitcoinPriceSchema } from '@/lib/schemas';

const price = { date: '2024-02-29', open: '100', high: 110, low: 90, close: 105, volume: '0' };

describe('market row contracts', () => {
    it('accepts SQL numeric strings and real calendar dates', () => {
        expect(BitcoinPriceSchema.parse(price)).toMatchObject({ open: 100, volume: 0 });
        expect(BitcoinPriceSchema.parse({ ...price, date: new Date('2024-02-29T00:00:00Z') }).date).toMatch(/^2024-02-29/);
    });

    it.each([{}, { ...price, date: undefined }, { ...price, date: '2024-02-30' },
        { ...price, date: new Date('invalid') }, { ...price, date: 'undefined' },
        ...[null, undefined, '', ' ', false, Infinity, 'Infinity', NaN].map(open => ({ ...price, open })),
        { ...price, rsi: Infinity }, { ...price, volume: null },
    ])('rejects malformed rows without fabricating prices: %p', row => {
        expect(BitcoinPriceSchema.safeParse(row).success).toBe(false);
    });

    it('rejects missing aggregate data', () => {
        expect(AggregatedDataSchema.safeParse({}).success).toBe(false);
    });
});
