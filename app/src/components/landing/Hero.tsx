'use client';

import Link from 'next/link';
import { theme } from '@/theme';

interface HeroProps {
    onStart?: () => void;
}

export default function Hero({ onStart }: HeroProps) {
    return (
        <div className="relative z-10 flex flex-col items-center justify-center min-h-screen text-center px-4 pt-20">
            {/* Announcement Banner */}
            <Link
                href="https://github.com/DOX69/Bitcoin-analysis/blob/main/README.md"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full mb-8 backdrop-blur-sm cursor-pointer hover:scale-105 transition-transform"
                style={{
                    background: 'rgba(255, 107, 53, 0.1)',
                    border: '1px solid rgba(255, 107, 53, 0.3)',
                }}
            >
                <span className="text-sm text-gray-300">New version coming soon!</span>
                <span
                    className="text-sm font-medium flex items-center gap-1"
                    style={{ color: theme.colors.primary.orange }}
                >
                    Read more →
                </span>
            </Link>

            {/* Main Headline */}
            <h1 className="text-5xl md:text-7xl lg:text-8xl font-bold mb-6 tracking-tight leading-tight">
                <span className="text-white italic">Master the Market with</span>
                <span className="block text-white italic">Elite Bitcoin Analysis</span>
            </h1>

            {/* Subtitle */}
            <p className="text-lg md:text-xl text-gray-400 max-w-2xl mb-12 leading-relaxed">
                Harness the power of B.ai's advanced neural networks to decode market
                <br />
                trends and identify high-probability trading opportunities in real-time.
            </p>

            {/* CTA Button */}
            <Link
                href="/dashboard"
                className="group relative px-8 py-4 rounded-lg font-semibold text-white transition-all hover:scale-105"
                style={{
                    background: `linear-gradient(135deg, ${theme.colors.primary.orange} 0%, #d85a2b 100%)`,
                    boxShadow: `0 0 40px ${theme.colors.primary.orange}40`,
                }}
            >
                <span className="relative z-10">Get started</span>
            </Link>
        </div>
    );
}
