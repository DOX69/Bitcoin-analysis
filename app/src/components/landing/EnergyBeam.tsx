'use client';

import { theme } from '@/theme';

export default function EnergyBeam() {
    return (
        <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">
            {/* Main Beam */}
            <div
                className="absolute top-0 left-1/2 -translate-x-1/2 w-[1px] h-screen bg-gradient-to-b from-transparent via-orange-500 to-transparent opacity-50"
                style={{
                    boxShadow: `0 0 100px 20px ${theme.colors.primary.orange}33`
                }}
            />

            {/* Glow Center */}
            <div
                className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full blur-[100px] opacity-20"
                style={{
                    background: `radial-gradient(circle, ${theme.colors.primary.orange} 0%, transparent 70%)`
                }}
            />

            {/* Grid Pattern Overlay */}
            <div className="absolute inset-0 bg-[linear-gradient(rgba(26,26,26,0.8)_1px,transparent_1px),linear-gradient(90deg,rgba(26,26,26,0.8)_1px,transparent_1px)] bg-[size:40px_40px] [mask-image:radial-gradient(ellipse_60%_60%_at_50%_50%,#000_70%,transparent_100%)] opacity-30" />
        </div>
    );
}
