export type ForecastPoint = { horizonWeeks: number; targetDate: string; q10?: number; q25: number; q50: number; q75: number; q90?: number };
export type ForecastEmission = {
    id: string;
    emissionDate: string;
    originWeek: string;
    originDate: string;
    issuedAt?: string;
    horizonEnd?: string;
    status: 'valid' | 'delayed' | 'invalidated';
    fx: Record<string, { rate: number; date: string }>;
    points: ForecastPoint[];
};
export type ForecastResponse = {
    status: 'available' | 'absent' | 'stale' | 'withdrawn' | 'invalid';
    model: { id: string; name: string; experimental?: boolean; horizonMonths?: 6 } | null;
    emissions: ForecastEmission[];
};
