'use client';

import React from 'react';
import { ArrowDown, ArrowUp } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

interface StatCardProps {
    title: string;
    value: string | number;
    icon?: React.ReactNode;
    trend?: 'up' | 'down' | 'neutral';
    subtitle?: string;
    loading?: boolean;
}

const StatCard: React.FC<StatCardProps> = ({
    title,
    value,
    icon,
    trend,
    subtitle,
    loading = false,
}) => {
    const getTrendIcon = () => {
        switch (trend) {
            case 'up': return <ArrowUp />;
            case 'down': return <ArrowDown />;
            default:
                return null;
        }
    };

    return (
        <Card className="stat-card">
            <CardHeader className="flex-row items-start justify-between p-0">
                <div className="flex items-center gap-2">
                    <CardTitle className="text-xs font-medium text-muted-foreground">{title}</CardTitle>
                    {trend && trend !== 'neutral' && <Badge variant={trend === 'down' ? 'destructive' : 'secondary'}>{getTrendIcon()}</Badge>}
                </div>
                {icon && <div className="text-muted-foreground">{icon}</div>}
            </CardHeader>
            <CardContent className="p-0 pt-2">
                {loading ? (
                    <Skeleton className="h-8 w-full bg-muted/70" />
                ) : (
                    <div className="text-xl font-bold text-white">
                        {typeof value === 'number'
                            ? value.toLocaleString('en-US', { minimumFractionDigits: 2 })
                            : value}
                    </div>
                )}
                {subtitle && <div className="mt-1 text-xs text-muted-foreground">{subtitle}</div>}
            </CardContent>
        </Card>
    );
};

export default StatCard;
