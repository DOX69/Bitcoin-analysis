'use client';

import { theme } from '@/theme';

const features = [
    {
        icon: '📊',
        title: 'Real-time Analytics',
        description: 'Track Bitcoin prices and market trends with live data from Databricks warehouse.',
    },
    {
        icon: '🤖',
        title: 'AI-Powered Insights',
        description: 'Advanced machine learning models predict market movements and identify patterns.',
    },
    {
        icon: '📈',
        title: 'Portfolio Tracking',
        description: 'Monitor your crypto investments with comprehensive performance dashboards.',
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
                        <div
                            key={index}
                            className="glass-card card-hover p-8 rounded-2xl text-center"
                        >
                            <div
                                className="w-16 h-16 mx-auto mb-6 rounded-xl flex items-center justify-center text-3xl"
                                style={{
                                    background: `linear-gradient(135deg, ${theme.colors.primary.orange}20 0%, ${theme.colors.secondary.charcoal} 100%)`,
                                    border: `1px solid ${theme.colors.primary.orange}30`,
                                }}
                            >
                                {feature.icon}
                            </div>
                            <h3 className="text-xl font-semibold text-white mb-3">
                                {feature.title}
                            </h3>
                            <p className="text-gray-400 leading-relaxed">
                                {feature.description}
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
