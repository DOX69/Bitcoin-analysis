'use client';

import React from 'react';

interface StatCardProps {
    title: string;
    value: string | number;
    icon?: React.ReactNode;
    trend?: 'up' | 'down' | 'neutral';
    trendColor?: string;
    subtitle?: string;
    loading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({
    title,
    value,
    icon,
    trend,
    trendColor,
    subtitle,
    loading = false,
}) => {
    const getTrendIcon = () => {
        switch (trend) {
            case 'up':
                return (
                    <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 11l5-5m0 0l5 5m-5-5v12" />
                    </svg>
                );
            case 'down':
                return (
                    <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 13l-5 5m0 0l-5-5m5 5V6" />
                    </svg>
                );
            default:
                return null;
        }
    };

    return (
        <div className="stat-card">
            <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 uppercase tracking-wide">{title}</span>
                    {getTrendIcon()}
                </div>
                {icon && <div className="text-gray-500">{icon}</div>}
            </div>

            {loading ? (
                <div className="h-8 bg-gray-700/50 rounded animate-pulse" />
            ) : (
                <div className={`text-xl font-bold ${trendColor || 'text-white'}`}>
                    {typeof value === 'number'
                        ? value.toLocaleString('en-US', { minimumFractionDigits: 2 })
                        : value}
                </div>
            )}

            {subtitle && (
                <div className="text-xs text-gray-500 mt-1">{subtitle}</div>
            )}
        </div>
    );
};

export default StatCard;
