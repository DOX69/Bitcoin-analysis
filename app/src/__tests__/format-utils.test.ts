import { formatDate } from '@/lib/format-utils';

describe('calendar date formatting', () => {
    it('does not shift a date-only value in a western timezone', () => {
        const previousTimezone = process.env.TZ;
        process.env.TZ = 'America/Los_Angeles';

        try {
            expect(formatDate('2024-01-01')).toBe("01 Janv '24");
        } finally {
            process.env.TZ = previousTimezone;
        }
    });
});
