'use client';

import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts';
import { theme } from '@/theme';

const AuthPreviewChart = () => {
    // Static dummy data for the preview
    const data = [
        { time: '10:00', price: 42000 },
        { time: '10:05', price: 42100 },
        { time: '10:10', price: 42050 },
        { time: '10:15', price: 42200 },
        { time: '10:20', price: 42150 },
        { time: '10:25', price: 42300 },
        { time: '10:30', price: 42250 },
        { time: '10:35', price: 42400 },
        { time: '10:40', price: 42350 },
        { time: '10:45', price: 42500 },
    ];

    return (
        <div className="w-full h-full bg-secondary-black rounded-lg p-4 border border-secondary-charcoal/30 shadow-lg">
            <div className="mb-4">
                <h3 className="text-secondary-gray text-sm font-medium">Bitcoin Price (Live)</h3>
                <div className="flex items-baseline gap-2">
                    <span className="text-text-light text-xl font-bold">$42,500.00</span>
                    <span className="text-accents-success text-xs font-medium">+1.2%</span>
                </div>
            </div>
            <div className="h-[120px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data}>
                        <Line
                            type="monotone"
                            dataKey="price"
                            stroke={theme.colors.primary.orange}
                            strokeWidth={2}
                            dot={false}
                            activeDot={{ r: 4, fill: theme.colors.primary.orange }}
                        />
                        {/* Minimal axes for cleaner look */}
                        <YAxis domain={['auto', 'auto']} hide />
                        <XAxis dataKey="time" hide />
                        <Tooltip
                            contentStyle={{ backgroundColor: theme.colors.secondary.black, border: 'none', borderRadius: '4px' }}
                            itemStyle={{ color: theme.colors.primary.orange }}
                            labelStyle={{ display: 'none' }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};

export default AuthPreviewChart;
