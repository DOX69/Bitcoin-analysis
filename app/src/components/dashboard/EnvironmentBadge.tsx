'use client';

import React from 'react';

const EnvironmentBadge: React.FC = () => {
    const env = process.env.NEXT_PUBLIC_APP_ENV || 'development';
    const isProd = env === 'production';

    return (
        <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all duration-300 ${isProd
                    ? 'bg-red-500/10 border-red-500/30 text-red-400'
                    : 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                }`}
            title={`Current Environment: ${env.toUpperCase()}`}
        >
            <div className={`w-2 h-2 rounded-full ${isProd ? 'bg-red-500' : 'bg-blue-500'} ${isProd ? '' : 'animate-pulse'}`} />
            <span className="text-[10px] font-bold tracking-wider uppercase">
                {isProd ? 'PROD' : 'DEV'}
            </span>
        </div>
    );
};

export default EnvironmentBadge;
