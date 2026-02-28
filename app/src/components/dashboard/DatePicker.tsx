'use client';

import React, { useState, useRef, useEffect } from 'react';

interface DatePickerProps {
    label: string;
    value: string;
    onChange: (date: string) => void;
}

const DatePicker: React.FC<DatePickerProps> = ({ label, value, onChange }) => {
    const [isOpen, setIsOpen] = useState(false);
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const containerRef = useRef<HTMLDivElement>(null);

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const daysInMonth = (year: number, month: number) => new Date(year, month + 1, 0).getDate();
    const firstDayOfMonth = (year: number, month: number) => new Date(year, month, 1).getDay();

    const months = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ];

    const handlePrevMonth = () => {
        setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
    };

    const handleNextMonth = () => {
        setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
    };

    const handleDateSelect = (day: number) => {
        const selectedDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
        // Format as YYYY-MM-DD using local components to avoid UTC offset issues
        const y = selectedDate.getFullYear();
        const m = String(selectedDate.getMonth() + 1).padStart(2, '0');
        const d = String(selectedDate.getDate()).padStart(2, '0');
        const formatted = `${y}-${m}-${d}`;
        onChange(formatted);
        setIsOpen(false);
    };

    const renderCalendar = () => {
        const year = currentMonth.getFullYear();
        const month = currentMonth.getMonth();
        const days = daysInMonth(year, month);
        const startDay = firstDayOfMonth(year, month);

        const prevMonthDays = daysInMonth(year, month - 1);
        const calendarDays = [];

        for (let i = startDay - 1; i >= 0; i--) {
            calendarDays.push({ day: prevMonthDays - i, current: false });
        }

        for (let i = 1; i <= days; i++) {
            calendarDays.push({ day: i, current: true });
        }

        const remaining = 42 - calendarDays.length;
        for (let i = 1; i <= remaining; i++) {
            calendarDays.push({ day: i, current: false });
        }

        return calendarDays;
    };

    // Use a fixed time to avoid timezone jumping during parsing
    const displayDate = value ? new Date(value + 'T00:00:00').toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : label;

    return (
        <div className="relative" ref={containerRef}>
            <div
                onClick={() => setIsOpen(!isOpen)}
                className={`flex items-center gap-2 px-3 py-1.5 bg-[#1c1c1c] rounded-lg border transition-all cursor-pointer group select-none ${isOpen ? 'border-[#F7931A]' : 'border-gray-800 hover:border-gray-600'
                    }`}
            >
                <svg className={`w-4 h-4 ${isOpen ? 'text-[#F7931A]' : 'text-gray-400 group-hover:text-[#F7931A]'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <span className="text-sm text-gray-300 min-w-[90px]">{displayDate}</span>
                <svg className={`w-4 h-4 transition-transform ${isOpen ? 'text-[#F7931A] rotate-180' : 'text-gray-500 group-hover:text-[#F7931A]'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </div>

            {isOpen && (
                <div className="absolute top-full left-0 mt-2 w-[280px] bg-[#1A1A1A] rounded-lg shadow-2xl z-50 p-4 border border-gray-800 overflow-hidden">
                    <div className="flex items-center justify-between mb-4 px-1">
                        <div className="flex items-center gap-1 group cursor-pointer">
                            <span className="text-white font-bold text-base hover:text-[#F7931A] transition-colors">
                                {months[currentMonth.getMonth()]} {currentMonth.getFullYear()}
                            </span>
                            <svg className="w-4 h-4 text-gray-400 group-hover:text-[#F7931A]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </div>
                        <div className="flex gap-1">
                            <button onClick={handlePrevMonth} className="p-1.5 hover:bg-gray-800 rounded-md text-gray-400 hover:text-white transition-colors">
                                <svg className="w-5 h-5 -rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                                </svg>
                            </button>
                            <button onClick={handleNextMonth} className="p-1.5 hover:bg-gray-800 rounded-md text-gray-400 hover:text-white transition-colors">
                                <svg className="w-5 h-5 rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                                </svg>
                            </button>
                        </div>
                    </div>

                    <div className="grid grid-cols-7 gap-0 mb-2">
                        {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map(day => (
                            <div key={day} className="text-center text-xs font-medium text-gray-500 py-2">
                                {day}
                            </div>
                        ))}
                    </div>

                    <div className="grid grid-cols-7 gap-1">
                        {renderCalendar().map((item, idx) => {
                            const isSelected = item.current && value &&
                                parseInt(value.split('-')[2]) === item.day &&
                                parseInt(value.split('-')[1]) === currentMonth.getMonth() + 1 &&
                                parseInt(value.split('-')[0]) === currentMonth.getFullYear();

                            return (
                                <button
                                    key={idx}
                                    onClick={() => item.current && handleDateSelect(item.day)}
                                    className={`text-center py-2 text-sm font-medium transition-all ${item.current
                                            ? 'text-white hover:bg-gray-800 cursor-pointer'
                                            : 'text-gray-600 pointer-events-none'
                                        } ${isSelected
                                            ? 'bg-[#F7931A] text-black hover:bg-[#F7931A]/90 rounded-sm font-bold shadow-sm'
                                            : 'rounded-md'
                                        }`}
                                >
                                    {item.day}
                                </button>
                            );
                        })}
                    </div>

                    <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-800 px-1">
                        <button
                            onClick={(e) => { e.stopPropagation(); onChange(''); setIsOpen(false); }}
                            className="text-sm font-bold text-[#F7931A] hover:text-[#e08618] transition-colors"
                        >
                            Clear
                        </button>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                const today = new Date();
                                handleDateSelect(today.getDate());
                            }}
                            className="text-sm font-bold text-[#F7931A] hover:text-[#e08618] transition-colors"
                        >
                            Today
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DatePicker;
