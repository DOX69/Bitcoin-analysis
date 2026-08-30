import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const KPI_DATA = [
    { label: 'BTC Price', value: '$68,429.15', change: '+2.4%', isPositive: true },
    { label: '24h Volume', value: '$24.5B', change: '+5.1%', isPositive: true },
    { label: 'Market Cap', value: '$1.35T', change: '-0.8%', isPositive: false },
];

export default function AuthKPIs() {
    return (
        <div className="grid w-full max-w-sm grid-cols-1 gap-4">
            {KPI_DATA.map((kpi) => (
                <Card key={kpi.label} className="border-white/10 bg-white/5 text-white shadow-xl backdrop-blur-md transition-transform hover:scale-105">
                    <CardHeader className="flex-row items-start justify-between p-4">
                        <CardTitle className="text-sm font-medium text-gray-400">{kpi.label}</CardTitle>
                        <Badge variant={kpi.isPositive ? 'secondary' : 'destructive'}>{kpi.change}</Badge>
                    </CardHeader>
                    <CardContent className="p-4 pt-0">
                        <div className="text-2xl font-bold tracking-tight">{kpi.value}</div>
                    </CardContent>
                </Card>
            ))}
        </div>
    );
}
