
import type { Currency } from './bitcoin-data-server';

export const formatPrice = (value: number): string => {
    return value.toLocaleString('fr-FR', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).replace(/\s/g, ' ');
};

export const getCurrencySymbol = (currency: Currency): string => {
    switch (currency) {
        case 'USD':
            return '$';
        case 'EUR':
            return '€';
        case 'CHF':
            return 'CHF';
        default:
            return '$';
    }
};

export const formatPriceWithCurrency = (value: number, currency: Currency): string => {
    const symbol = getCurrencySymbol(currency);
    const formatted = formatPrice(value);
    return `${symbol}${formatted}`;
};

export const parseCalendarDate = (value: string): Date => {
    const calendarDate = value.match(/^\d{4}-\d{2}-\d{2}/)?.[0];
    return new Date(calendarDate ? `${calendarDate}T00:00:00.000Z` : value);
};

export const getCalendarDateTimestamp = (value: string): number => {
    return parseCalendarDate(value).getTime();
};

export const formatDate = (dateStr: string): string => {
    const date = parseCalendarDate(dateStr);
    const day = date.getUTCDate().toString().padStart(2, '0');
    const monthMap: Record<number, string> = {
        0: 'Janv',
        1: 'Févr',
        2: 'Mars',
        3: 'Avr',
        4: 'Mai',
        5: 'Juin',
        6: 'Juil',
        7: 'Août',
        8: 'Sept',
        9: 'Oct',
        10: 'Nov',
        11: 'Déc'
    };
    const month = monthMap[date.getUTCMonth()];
    const year = date.getUTCFullYear().toString().slice(-2);
    return `${day} ${month} '${year}`;
};

export const formatTooltipTime = (): string => {
    // Since data is daily, we mock the time as per user example
    // Or we could use context.label if it had time.
    return "14:30 UTC+1";
};
