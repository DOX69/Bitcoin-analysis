'use client';

import { BarChart3, Database, Cloud } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const features = [
    {
        icon: BarChart3,
        title: 'Daily Market Data',
        description: 'Track Bitcoin prices and market trends with data updated daily.',
    },
    {
        icon: Database,
        title: 'PostgreSQL History',
        description: 'Review historical Bitcoin market data stored in PostgreSQL.',
    },
    {
        icon: Cloud,
        title: 'Railway Hosting',
        description: 'The application and its daily data pipeline are hosted on Railway.',
    },
];

export default function Features() {
    return (
        <section id="features" className="relative py-24 px-4">
            <div className="max-w-6xl mx-auto">
                {/* Section Header */}
                <div className="text-center mb-16">
                    <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                        Powerful Features
                    </h2>
                    <p className="text-gray-400 max-w-2xl mx-auto">
                        Everything you need for professional cryptocurrency analysis
                    </p>
                </div>

                {/* Features Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                    {features.map((feature, index) => (
                        <Card key={index} className="border-primary/15 bg-card/80 p-8 text-center transition-transform hover:-translate-y-1">
                            <CardHeader className="items-center gap-6 p-0">
                                <div className="flex size-16 items-center justify-center rounded-xl border border-primary/30 bg-primary/10 text-primary">
                                    <feature.icon />
                                </div>
                                <CardTitle className="text-xl text-foreground">{feature.title}</CardTitle>
                            </CardHeader>
                            <CardContent className="p-0 pt-3">
                                <p className="leading-relaxed text-muted-foreground">{feature.description}</p>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        </section>
    );
}
