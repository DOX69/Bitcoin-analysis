'use client';

import React, { useState, useRef, useEffect } from 'react';
import { ChevronDown, BarChart2, Check } from 'lucide-react';

interface IndicatorSelectorProps {
    selectedIndicators: Set<string>;
    onToggleIndicator: (indicator: string) => void;
}

const INDICATORS = [
    { id: 'rsi', label: 'RSI', description: 'Relative Strength Index' },
    { id: 'macd', label: 'MACD', description: 'Moving Average Convergence Divergence' },
    { id: 'sma', label: '3 SMA', description: '7, 50, 200-day Simple Moving Averages' },
    { id: 'ema', label: '3 EMA', description: '7, 50, 200-day Exponential Moving Averages' },
];

export default function IndicatorSelector({ selectedIndicators, onToggleIndicator }: IndicatorSelectorProps) {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <div className="relative inline-block text-left" ref={dropdownRef}>
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className={`flex items-center gap-2 px-4 py-2 bg-gray-800/50 hover:bg-gray-700/50 backdrop-blur-md border border-gray-700 rounded-lg text-xs font-medium transition-all duration-200 focus:outline-none ${isOpen ? 'ring-2 ring-[#F7931A]/50 border-[#F7931A]/50' : ''}`}
                aria-haspopup="true"
                aria-expanded={isOpen}
            >
                <BarChart2 className={`w-4 h-4 ${selectedIndicators.size > 0 ? 'text-[#F7931A]' : 'text-gray-400'}`} />
                <span className={selectedIndicators.size > 0 ? 'text-white' : 'text-gray-400'}>Indicators</span>
                {selectedIndicators.size > 0 && (
                    <span className="flex items-center justify-center w-4 h-4 ml-1 bg-[#F7931A] text-black text-[10px] font-bold rounded-full">
                        {selectedIndicators.size}
                    </span>
                )}
                <ChevronDown className={`w-4 h-4 ml-1 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
            </button>

            {isOpen && (
                <div className="absolute right-0 mt-2 w-72 origin-top-right bg-gray-900/90 backdrop-blur-xl border border-gray-700 rounded-xl shadow-2xl z-50 overflow-hidden animate-in fade-in zoom-in duration-200">
                    <div className="p-2 space-y-1">
                        {INDICATORS.map((indicator) => {
                            const isSelected = selectedIndicators.has(indicator.id);
                            return (
                                <button
                                    key={indicator.id}
                                    onClick={() => onToggleIndicator(indicator.id)}
                                    aria-pressed={isSelected}
                                    className={`w-full flex items-start gap-3 p-3 rounded-lg transition-colors group ${isSelected ? 'bg-[#F7931A]/10' : 'hover:bg-gray-800'
                                        }`}
                                >
                                    <div className={`mt-0.5 flex-shrink-0 w-4 h-4 rounded border flex items-center justify-center transition-colors ${isSelected ? 'bg-[#F7931A] border-[#F7931A]' : 'border-gray-600 group-hover:border-gray-500'
                                        }`}>
                                        {isSelected && <Check className="w-3 h-3 text-black" />}
                                    </div>
                                    <div className="flex flex-col text-left">
                                        <span className={`text-sm font-semibold transition-colors ${isSelected ? 'text-[#F7931A]' : 'text-gray-200'
                                            }`}>
                                            {indicator.label}
                                        </span>
                                        <span className="text-[11px] text-gray-500 line-clamp-1">
                                            {indicator.description}
                                        </span>
                                    </div>
                                </button>
                            );
                        })}
                    </div>
                </div>
            )}
        </div>
    );
}
