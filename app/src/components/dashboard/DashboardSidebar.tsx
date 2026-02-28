'use client';

import React from 'react';

interface DashboardSidebarProps {
    activeTab?: 'overview' | 'risk';
    onTabChange?: (tab: 'overview' | 'risk') => void;
}

interface TimeFilter {
    label: string;
    value: string;
    active?: boolean;
}

const timeFilters: TimeFilter[] = [
    { label: '1W', value: '1w' },
    { label: '1M', value: '1m' },
    { label: '6M', value: '6m', active: true },
    { label: 'YTD', value: 'ytd' },
    { label: 'ALL', value: 'all' },
];

const DashboardSidebar: React.FC<DashboardSidebarProps> = ({
    activeTab = 'overview',
    onTabChange
}) => {
    const [selectedTime, setSelectedTime] = React.useState('6m');
    const [startDate, setStartDate] = React.useState('13 Jul 2025');
    const [endDate, setEndDate] = React.useState('13 Jul 2025');

    return (
        <aside className="dashboard-sidebar">
            {/* Tab Switcher */}
            <div className="flex bg-gray-800/50 rounded-lg p-1 mb-6">
                <button
                    onClick={() => onTabChange?.('overview')}
                    className={`flex-1 py-2 px-4 rounded-md text-sm font-medium smooth-transition ${activeTab === 'overview'
                            ? 'bg-gray-700 text-white'
                            : 'text-gray-400 hover:text-white'
                        }`}
                >
                    Overview
                </button>
                <button
                    onClick={() => onTabChange?.('risk')}
                    className={`flex-1 py-2 px-4 rounded-md text-sm font-medium smooth-transition ${activeTab === 'risk'
                            ? 'bg-gray-700 text-white'
                            : 'text-gray-400 hover:text-white'
                        }`}
                >
                    Risk
                </button>
            </div>

            {/* Time Period Filters */}
            <div className="flex gap-2 mb-4">
                {timeFilters.map((filter) => (
                    <button
                        key={filter.value}
                        onClick={() => setSelectedTime(filter.value)}
                        className={`px-3 py-1.5 rounded-md text-xs font-medium smooth-transition ${selectedTime === filter.value
                                ? 'bg-energy-orange text-black'
                                : 'bg-gray-800/50 text-gray-400 hover:text-white hover:bg-gray-700'
                            }`}
                    >
                        {filter.label}
                    </button>
                ))}
            </div>

            {/* Date Range Picker */}
            <div className="flex gap-2 items-center">
                <div className="flex items-center gap-2 px-3 py-2 bg-gray-800/50 rounded-lg border border-gray-700">
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span className="text-sm text-gray-300">{startDate}</span>
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </div>
                <span className="text-gray-500">→</span>
                <div className="flex items-center gap-2 px-3 py-2 bg-gray-800/50 rounded-lg border border-gray-700">
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                    </svg>
                    <span className="text-sm text-gray-300">{endDate}</span>
                    <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                </div>
            </div>
        </aside>
    );
};

export default DashboardSidebar;
