import { formatMarketDate } from '@/lib/format-utils';

describe('calendar date formatting', () => {
    it('does not shift a date-only value in a western timezone', () => {
        const previousTimezone = process.env.TZ;
        process.env.TZ = 'America/Los_Angeles';

        try {
            expect(formatMarketDate('2024-01-01')).toBe('1 Jan 2024');
        } finally {
            process.env.TZ = previousTimezone;
        }
    });
});
