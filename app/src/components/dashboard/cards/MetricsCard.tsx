import React from 'react';

interface MetricsCardProps {
    title: string;
    value: string | number;
    change?: number;
    changePercent?: number;
    icon?: React.ReactNode;
    loading?: boolean;
}

const MetricsCard: React.FC<MetricsCardProps> = ({
    title,
    value,
    change,
    changePercent,
    icon,
    loading = false,
}) => {
    const isPositive = change ? change > 0 : false;
    const changeColor = isPositive ? 'text-green-400' : 'text-red-400';

    return (
        <div className="glass-card rounded-xl p-6 card-hover gradient-border">
            <div className="flex items-start justify-between mb-4">
                <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wide">
                    {title}
                </h3>
                {icon && (
                    <div className="text-energy-yellow">
                        {icon}
                    </div>
                )}
            </div>

            {loading ? (
                <div className="space-y-3">
                    <div className="h-10 bg-gray-700/50 rounded animate-pulse loading-pulse" />
                    <div className="h-6 bg-gray-700/30 rounded w-24 animate-pulse loading-pulse" />
                </div>
            ) : (
                <>
                    <div className="text-4xl font-bold gradient-text mb-2 number-animate">
                        {typeof value === 'number'
                            ? value.toLocaleString('en-US', {
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2,
                            })
                            : value
                        }
                    </div>

                    {(change !== undefined || changePercent !== undefined) && (
                        <div className={`flex items-center gap-2 text-sm font-medium ${changeColor}`}>
                            <span>
                                {isPositive ? '↑' : '↓'}
                            </span>
                            {change !== undefined && (
                                <span>
                                    ${Math.abs(change).toLocaleString('en-US', {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2,
                                    })}
                                </span>
                            )}
                            {changePercent !== undefined && (
                                <span>
                                    ({isPositive ? '+' : ''}{changePercent.toFixed(2)}%)
                                </span>
                            )}
                            <span className="text-gray-400 ml-1">24h</span>
                        </div>
                    )}
                </>
            )}
        </div>
    );
};

export default MetricsCard;
