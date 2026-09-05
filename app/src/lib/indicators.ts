import type { BitcoinPrice } from '@/lib/schemas';

type IndicatorSeries = {
    key: keyof Pick<BitcoinPrice, 'rsi' | 'macd' | 'macd_signal' | 'macd_hist' | 'sma_7' | 'sma_50' | 'sma_200' | 'ema_7' | 'ema_50' | 'ema_200'>;
    label: string;
    price: boolean;
    color?: string;
};

export const INDICATORS = {
    rsi: {
        label: 'RSI', description: 'Relative Strength Index',
        mobileLabel: 'RSI', mobileDetail: 'Relative Strength Index',
        series: [{ key: 'rsi', label: 'RSI', price: false, color: '#ffffff' }],
    },
    macd: {
        label: 'MACD', description: 'Moving Average Convergence Divergence',
        mobileLabel: 'MACD', mobileDetail: 'Momentum and signal',
        series: [
            { key: 'macd', label: 'MACD', price: false, color: '#3b82f6' },
            { key: 'macd_signal', label: 'Signal', price: false, color: '#f97316' },
            { key: 'macd_hist', label: 'Histogram', price: false },
        ],
    },
    sma: {
        label: '3 SMA', description: '7, 50, 200-day Simple Moving Averages',
        mobileLabel: 'SMA', mobileDetail: 'Simple averages · 7, 50, 200 days',
        series: [
            { key: 'sma_7', label: 'SMA 7', price: true, color: 'rgba(56, 189, 248, 0.8)' },
            { key: 'sma_50', label: 'SMA 50', price: true, color: 'rgba(168, 85, 247, 0.8)' },
            { key: 'sma_200', label: 'SMA 200', price: true, color: 'rgba(236, 72, 153, 0.8)' },
        ],
    },
    ema: {
        label: '3 EMA', description: '7, 50, 200-day Exponential Moving Averages',
        mobileLabel: 'EMA', mobileDetail: 'Exponential averages · 7, 50, 200 days',
        series: [
            { key: 'ema_7', label: 'EMA 7', price: true, color: 'rgba(56, 189, 248, 0.6)' },
            { key: 'ema_50', label: 'EMA 50', price: true, color: 'rgba(168, 85, 247, 0.6)' },
            { key: 'ema_200', label: 'EMA 200', price: true, color: 'rgba(236, 72, 153, 0.6)' },
        ],
    },
} as const satisfies Record<string, {
    label: string; description: string; mobileLabel: string; mobileDetail: string;
    series: readonly IndicatorSeries[];
}>;

export type IndicatorId = keyof typeof INDICATORS;
export const DESKTOP_INDICATOR_ORDER: readonly IndicatorId[] = ['rsi', 'macd', 'sma', 'ema'];
export const MOBILE_INDICATOR_ORDER: readonly IndicatorId[] = ['sma', 'ema', 'rsi', 'macd'];
