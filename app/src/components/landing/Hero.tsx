'use client';

import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { buttonVariants } from '@/components/ui/button';

export default function Hero() {
    return (
        <div className="relative z-10 flex flex-col items-center justify-center min-h-screen text-center px-4 pt-20">
            {/* Announcement Banner */}
            <Link
                href="https://github.com/DOX69/Bitcoin-analysis/blob/main/README.md"
                target="_blank"
                rel="noopener noreferrer"
                className="mb-8 transition-transform hover:scale-105"
            >
                <Badge variant="outline" className="gap-2 border-primary/30 bg-primary/10 px-4 py-2 text-muted-foreground">
                    New version coming soon!
                    <span className="flex items-center gap-1 text-primary">
                        Read more <ArrowRight data-icon="inline-end" />
                    </span>
                </Badge>
            </Link>

            {/* Main Headline */}
            <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold mb-6 tracking-tight leading-tight">
                <span className="text-white italic">Master the Market with</span>
                <span className="block text-white italic">Elite Bitcoin Analysis</span>
            </h1>

            {/* Subtitle */}
            <p className="text-lg md:text-xl text-gray-400 max-w-2xl mb-12 leading-relaxed">
                Explore Bitcoin price history and technical indicators with PostgreSQL data
                <br />
                updated daily.
            </p>

            {/* CTA Button */}
            <Link href="/login" className={buttonVariants({ size: 'lg', className: 'px-8 shadow-[0_0_40px_rgba(255,107,53,0.25)] transition-transform hover:scale-105' })}>
                Get started
            </Link>
        </div>
    );
}
