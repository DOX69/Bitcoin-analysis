
import type { BitcoinPrice } from './schemas';
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

export const formatMarketDate = (value: string): string => new Intl.DateTimeFormat('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
}).format(parseCalendarDate(value));

export const formatPriceDate = (price: Pick<BitcoinPrice, 'date' | 'aggregation'>): string => {
    if (price.aggregation === 'monthly') {
        const month = new Intl.DateTimeFormat('en-GB', {
            month: 'short', year: 'numeric', timeZone: 'UTC',
        }).format(parseCalendarDate(price.date));
        return `${month} (monthly aggregate)`;
    }
    return formatMarketDate(price.date);
};
