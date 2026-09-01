'use client';

import { BarChart3, Database, Gauge } from 'lucide-react';

const features = [
    {
        icon: BarChart3,
        title: 'Daily market snapshots',
        description: 'Review Bitcoin prices, volume, 24-hour change, highs, lows, and RSI from the PostgreSQL dataset.',
    },
    {
        icon: Database,
        title: 'Historical context',
        description: 'Change the period, date range, currency, scale, and chart type without leaving the timeline.',
    },
    {
        icon: Gauge,
        title: 'Technical layers',
        description: 'Compare RSI, MACD, SMA, and EMA overlays against the same Bitcoin price history.',
    },
];

export default function Features() {
    return (
        <section id="capabilities" className="relative px-4 py-24">
            <div className="max-w-6xl mx-auto">
                <div className="mb-12 max-w-2xl">
                    <h2 className="mb-4 text-balance text-3xl font-bold text-white md:text-4xl">
                        What the dashboard shows
                    </h2>
                    <p className="text-pretty text-muted-foreground">
                        A read-only view of Bitcoin market data. It does not place trades or create personal positions.
                    </p>
                </div>

                <div className="border-y border-border md:grid md:grid-cols-3">
                    {features.map((feature) => (
                        <article key={feature.title} className="border-b border-border px-2 py-8 last:border-b-0 md:border-b-0 md:border-r md:px-8 md:first:pl-0 md:last:border-r-0 md:last:pr-0">
                            <feature.icon className="mx-auto mb-6 size-6 text-primary" aria-hidden="true" />
                            <h3 className="text-xl font-semibold text-foreground">{feature.title}</h3>
                            <p className="mt-3 max-w-[38ch] leading-relaxed text-muted-foreground">{feature.description}</p>
                        </article>
                    ))}
                </div>
            </div>
        </section>
    );
}
