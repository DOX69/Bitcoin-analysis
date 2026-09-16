export type ForecastPoint = { horizonWeeks?: number; horizonDays?: number; targetDate: string; q25: number; q50: number; q75: number };
export type ForecastEmission = {
    id: string;
    emissionDate: string;
    originWeek: string;
    originDate: string;
    status: 'valid' | 'delayed' | 'invalidated';
    fx: Record<string, { rate: number; date: string }>;
    points: ForecastPoint[];
};
export type ForecastResponse = {
    frequency?: 'daily' | 'weekly';
    experimental?: boolean;
    status: 'available' | 'absent' | 'stale' | 'withdrawn' | 'invalid';
    model: { id: string; name: string } | null;
    emissions: ForecastEmission[];
};
