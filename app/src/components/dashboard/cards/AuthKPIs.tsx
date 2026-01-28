import React from 'react';
import { theme } from '@/theme';

const KPI_DATA = [
    { label: 'BTC Price', value: '$68,429.15', change: '+2.4%', isPositive: true },
    { label: '24h Volume', value: '$24.5B', change: '+5.1%', isPositive: true },
    { label: 'Market Cap', value: '$1.35T', change: '-0.8%', isPositive: false },
];

export default function AuthKPIs() {
    return (
        <div className="grid grid-cols-1 gap-4 w-full max-w-sm">
            {KPI_DATA.map((kpi, index) => (
                <div
                    key={index}
                    className="flex flex-col p-4 rounded-xl border border-white/10 bg-white/5 backdrop-blur-md shadow-xl transition-transform hover:scale-105"
                >
                    <div className="flex justify-between items-start mb-2">
                        <span className="text-sm text-gray-400 font-medium">{kpi.label}</span>
                        <span className={`text-xs px-2 py-1 rounded-full ${kpi.isPositive
                                ? 'bg-green-500/20 text-green-400'
                                : 'bg-red-500/20 text-red-400'
                            }`}>
                            {kpi.change}
                        </span>
                    </div>
                    <div className="text-2xl font-bold text-white tracking-tight">
                        {kpi.value}
                    </div>
                </div>
            ))}
        </div>
    );
}
