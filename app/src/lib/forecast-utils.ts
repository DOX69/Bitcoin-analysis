import { BitcoinForecast } from '@/lib/schemas';

/**
 * Filter forecast data based on selected time filter.
 * Handles aggregation for 'all' filter and Duration limits for others.
 */
export const getForecastSlice = (
    initialForecastData: BitcoinForecast[],
    initialTime: string
): BitcoinForecast[] => {
    if (!initialForecastData.length) return [];

    if (initialTime === 'all') {
        // Monthly aggregation: filtered to 1st of each month (approx)
        const monthlyData: BitcoinForecast[] = [];
        let lastMonth = -1;

        initialForecastData.forEach(item => {
            const date = new Date(item.date_prices);
            const currentMonth = date.getMonth();

            if (currentMonth !== lastMonth) {
                monthlyData.push(item);
                lastMonth = currentMonth;
            }
        });
        return monthlyData;
    }

    let daysToSlice = 365; // Default max 1 year

    switch (initialTime) {
        case '1w': daysToSlice = 7; break;
        case '1m': daysToSlice = 30; break;
        case '6m': daysToSlice = 180; break;
        case '1y':
        case 'ytd':
            daysToSlice = 365; break;
        default: daysToSlice = 180;
    }

    return initialForecastData.slice(0, daysToSlice);
};
