import type { BitcoinMetrics } from '@/lib/schemas';
import { formatMarketDate } from '@/lib/format-utils';

export default function PriceFreshness({ observedAt, dataAgeDays }: Pick<BitcoinMetrics, 'observedAt' | 'dataAgeDays'>) {
    return (
        <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
            {observedAt ? <time dateTime={observedAt}>{formatMarketDate(observedAt)}</time> : <span>Observation date unavailable</span>}
            {dataAgeDays !== undefined && dataAgeDays > 1 && <span className="font-medium text-primary">{dataAgeDays} days old</span>}
            <span>Not live</span>
        </p>
    );
}
