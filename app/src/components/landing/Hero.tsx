'use client';

import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { buttonVariants } from '@/components/ui/button';

export default function Hero() {
    return (
        <div className="relative z-10 flex flex-col items-center justify-center min-h-screen text-center px-4 pt-20">
            <Badge variant="outline" className="mb-8 h-auto border-primary/30 bg-primary/10 px-4 py-2 text-primary">
                Daily PostgreSQL snapshots
            </Badge>

            <h1 className="mb-6 max-w-5xl text-balance text-5xl font-semibold leading-[1.05] tracking-tight text-white md:text-7xl lg:text-8xl">
                Trace Bitcoin moves through time
            </h1>

            <p className="mb-10 max-w-2xl text-pretty text-lg leading-relaxed text-muted-foreground md:text-xl">
                Explore price history, technical indicators, and daily PostgreSQL snapshots in one focused dashboard.
            </p>

            <Link href="/dashboard" className={buttonVariants({ size: 'lg', className: 'min-h-11 px-8' })}>
                Open market dashboard
            </Link>
        </div>
    );
}
