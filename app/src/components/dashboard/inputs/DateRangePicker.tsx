'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
    format,
    addMonths,
    subMonths,
    startOfMonth,
    endOfMonth,
    eachDayOfInterval,
    isSameMonth,
    isSameDay,
    isWithinInterval,
    startOfWeek,
    endOfWeek,
    subDays,
    startOfDay,
    endOfDay,
    isValid,
    parseISO,
    subYears,
    addYears,
    setYear,
    setMonth,
    getYear,
    getMonth,
    formatISO
} from 'date-fns';

interface DateRangePickerProps {
    startDate: string; // YYYY-MM-DD
    endDate: string;   // YYYY-MM-DD
    onChange: (start: string, end: string) => void;
}

const DateRangePicker: React.FC<DateRangePickerProps> = ({ startDate, endDate, onChange }) => {
    const [isOpen, setIsOpen] = useState(false);

    // Internal state for the picker (changes before Apply)
    const [tempStart, setTempStart] = useState<Date | null>(startDate ? new Date(startDate) : null);
    const [tempEnd, setTempEnd] = useState<Date | null>(endDate ? new Date(endDate) : null);

    // The month shown in the left calendar
    const [viewDate, setViewDate] = useState<Date>(startDate ? new Date(startDate) : new Date());

    // View mode for the left calendar
    const [leftViewMode, setLeftViewMode] = useState<'days' | 'months' | 'years'>('days');
    // View mode for the right calendar
    const [rightViewMode, setRightViewMode] = useState<'days' | 'months' | 'years'>('days');

    const [hoverDate, setHoverDate] = useState<Date | null>(null);
    const [inputValue, setInputValue] = useState('');

    const containerRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (startDate && endDate) {
            setTempStart(new Date(startDate));
            setTempEnd(new Date(endDate));
            setInputValue(`${startDate} ~ ${endDate}`);
        } else {
            if (startDate) setTempStart(new Date(startDate));
            if (endDate) setTempEnd(new Date(endDate));
            setInputValue('');
        }
    }, [startDate, endDate]);

    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
                if (startDate && endDate) {
                    setTempStart(new Date(startDate));
                    setTempEnd(new Date(endDate));
                    setInputValue(`${startDate} ~ ${endDate}`);
                } else {
                    if (startDate) setTempStart(new Date(startDate));
                    if (endDate) setTempEnd(new Date(endDate));
                }
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [startDate, endDate]);

    const handleDateClick = (day: Date) => {
        if (!tempStart || (tempStart && tempEnd)) {
            // Start new selection
            setTempStart(day);
            setTempEnd(null);
        } else {
            // Complete selection
            if (day < tempStart) {
                setTempEnd(tempStart);
                setTempStart(day);
            } else {
                setTempEnd(day);
            }
        }
    };

    const handleApply = () => {
        if (tempStart && tempEnd) {
            const s = format(tempStart, 'yyyy-MM-dd');
            const e = format(tempEnd, 'yyyy-MM-dd');
            onChange(s, e);
            setInputValue(`${s} ~ ${e}`);
            setIsOpen(false);
        }
    };

    const handleCancel = () => {
        setIsOpen(false);
        if (startDate && endDate) {
            setTempStart(new Date(startDate));
            setTempEnd(new Date(endDate));
            setInputValue(`${startDate} ~ ${endDate}`);
        } else {
            setTempStart(null);
            setTempEnd(null);
            setInputValue('');
        }
    };

    const selectPreset = (type: 'today' | 'yesterday' | 'last7' | 'last30' | 'thisMonth' | 'lastMonth' | 'last2Year' | 'last3Year' | 'last5Year' | 'last10Year' | 'last12Year') => {
        const today = startOfDay(new Date());
        let s: Date, e: Date;

        switch (type) {
            case 'today':
                s = today;
                e = today;
                break;
            case 'yesterday':
                s = subDays(today, 1);
                e = subDays(today, 1);
                break;
            case 'last7':
                s = subDays(today, 6);
                e = today;
                break;
            case 'last30':
                s = subDays(today, 29);
                e = today;
                break;
            case 'thisMonth':
                s = startOfMonth(today);
                e = endOfMonth(today);
                break;
            case 'lastMonth':
                const lastM = subMonths(today, 1);
                s = startOfMonth(lastM);
                e = endOfMonth(lastM);
                break;
            case 'last2Year':
                s = subYears(today, 2);
                e = today;
                break;
            case 'last3Year':
                s = subYears(today, 3);
                e = today;
                break;
            case 'last5Year':
                s = subYears(today, 5);
                e = today;
                break;
            case 'last10Year':
                s = subYears(today, 10);
                e = today;
                break;
            case 'last12Year':
                s = subYears(today, 12);
                e = today;
                break;
        }

        setTempStart(s);
        setTempEnd(e);
        setViewDate(s);
        setLeftViewMode('days');
        setRightViewMode('days');
        setInputValue(`${format(s, 'yyyy-MM-dd')} ~ ${format(e, 'yyyy-MM-dd')}`);
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const val = e.target.value;
        setInputValue(val);

        const parts = val.split('~').map(p => p.trim());
        if (parts.length === 2) {
            const s = new Date(parts[0]);
            const e = new Date(parts[1]);
            if (isValid(s) && isValid(e)) {
                setTempStart(s);
                setTempEnd(e);
                setViewDate(s);
            }
        }
    };

    const renderYears = (currentViewDate: Date, side: 'left' | 'right') => {
        const currentYear = getYear(currentViewDate);
        const startYear = currentYear - 12;
        const endYear = currentYear + 12;
        const years = [];
        for (let y = startYear; y <= endYear; y++) {
            years.push(y);
        }

        const handleYearClick = (y: number) => {
            if (side === 'left') {
                setViewDate(setYear(currentViewDate, y));
                setLeftViewMode('months');
            } else {
                // For the right calendar, currentViewDate is already addMonths(viewDate, 1).
                // We need to set the year for this date and then adjust viewDate (left calendar's date)
                // to maintain the 1-month offset.
                const newRightDate = setYear(currentViewDate, y);
                setViewDate(subMonths(newRightDate, 1));
                setRightViewMode('months');
            }
        };

        return (
            <div className="w-[280px] p-2">
                <div className="flex justify-between items-center mb-4 px-2">
                    <button onClick={() => setViewDate(subYears(viewDate, 25))} className="p-1 hover:bg-gray-800 rounded-full text-gray-400">
                        &lt;
                    </button>
                    <span className="font-bold text-gray-200">
                        {startYear} - {endYear}
                    </span>
                    <button onClick={() => setViewDate(addYears(viewDate, 25))} className="p-1 hover:bg-gray-800 rounded-full text-gray-400">
                        &gt;
                    </button>
                </div>
                <div className="grid grid-cols-3 gap-2">
                    {years.map(y => (
                        <button
                            key={y}
                            onClick={() => handleYearClick(y)}
                            className={`p-2 rounded hover:bg-gray-800 text-sm ${y === getYear(new Date()) ? 'text-[#F7931A] font-bold' : 'text-gray-300'}`}
                        >
                            {y}
                        </button>
                    ))}
                </div>
            </div>
        );
    };

    const renderMonths = (currentViewDate: Date, side: 'left' | 'right') => {
        const months = [
            'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
        ];

        const handleMonthClick = (mIndex: number) => {
            if (side === 'left') {
                setViewDate(setMonth(currentViewDate, mIndex));
                setLeftViewMode('days');
            } else {
                // For the right calendar, currentViewDate is already addMonths(viewDate, 1).
                // We need to set the month for this date and then adjust viewDate (left calendar's date)
                // to maintain the 1-month offset.
                const newRightDate = setMonth(currentViewDate, mIndex);
                setViewDate(subMonths(newRightDate, 1));
                setRightViewMode('days');
            }
        };

        return (
            <div className="w-[280px] p-2">
                <div className="flex justify-between items-center mb-4 px-2">
                    <button onClick={() => setViewDate(subYears(viewDate, 1))} className="p-1 hover:bg-gray-800 rounded-full text-gray-400">
                        &lt;
                    </button>
                    <button
                        onClick={() => side === 'left' ? setLeftViewMode('years') : setRightViewMode('years')}
                        className="font-bold text-gray-200 hover:text-[#F7931A]"
                    >
                        {getYear(currentViewDate)}
                    </button>
                    <button onClick={() => setViewDate(addYears(viewDate, 1))} className="p-1 hover:bg-gray-800 rounded-full text-gray-400">
                        &gt;
                    </button>
                </div>
                <div className="grid grid-cols-3 gap-2">
                    {months.map((m, i) => (
                        <button
                            key={m}
                            onClick={() => handleMonthClick(i)}
                            className={`p-2 rounded hover:bg-gray-800 text-sm ${i === getMonth(new Date()) && getYear(currentViewDate) === getYear(new Date()) ? 'text-[#F7931A] font-bold' : 'text-gray-300'}`}
                        >
                            {m}
                        </button>
                    ))}
                </div>
            </div>
        );
    };

    const renderCalendarDays = (monthDate: Date, isLeft: boolean) => {
        const monthStart = startOfMonth(monthDate);
        const monthEnd = endOfMonth(monthStart);
        const startDateMonth = startOfWeek(monthStart);
        const endDateMonth = endOfWeek(monthEnd);

        const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

        return (
            <div className="w-[280px] p-2">
                <div className="flex justify-center items-center mb-4 px-2 gap-1">
                    {/* Header: Month Year (Clickable) */}
                    <button
                        onClick={() => isLeft ? setLeftViewMode('months') : setRightViewMode('months')}
                        className="font-bold text-gray-200 hover:text-[#F7931A] transition-colors"
                    >
                        {format(monthDate, 'MMM').toUpperCase()}
                    </button>
                    <button
                        onClick={() => isLeft ? setLeftViewMode('years') : setRightViewMode('years')}
                        className="font-bold text-gray-200 hover:text-[#F7931A] transition-colors"
                    >
                        {format(monthDate, 'yyyy')}
                    </button>
                </div>

                <div className="grid grid-cols-7 mb-2">
                    {weekDays.map(d => (
                        <div key={d} className="text-center text-xs text-gray-500 font-medium py-1">{d}</div>
                    ))}
                </div>

                <div className="grid grid-cols-7 gap-y-1">
                    {eachDayOfInterval({ start: startDateMonth, end: endDateMonth }).map((d, idx) => {
                        const isCurrentMonth = isSameMonth(d, monthStart);
                        const isSelectedStart = tempStart && isSameDay(d, tempStart);
                        const isSelectedEnd = tempEnd && isSameDay(d, tempEnd);
                        const isInRange = tempStart && tempEnd && isWithinInterval(d, { start: tempStart, end: tempEnd });
                        const isPreviewRange = !tempEnd && tempStart && hoverDate && (
                            (d >= tempStart && d <= hoverDate) || (d <= tempStart && d >= hoverDate)
                        );

                        return (
                            <div
                                key={idx}
                                className={`
                                    relative w-full aspect-square flex items-center justify-center text-sm cursor-pointer transition-all
                                    ${!isCurrentMonth ? 'text-gray-700' : 'text-gray-300'}
                                    ${isSelectedStart ? 'bg-[#F7931A] text-black rounded-l-md z-10' : ''}
                                    ${isSelectedEnd ? 'bg-[#F7931A] text-black rounded-r-md z-10' : ''}
                                    ${(isSelectedStart && isSelectedEnd) ? 'rounded-md' : ''}
                                    ${(!isSelectedStart && !isSelectedEnd && isInRange) ? 'bg-[#F7931A]/20' : ''}
                                    ${(!isSelectedStart && !isSelectedEnd && !isInRange && isPreviewRange) ? 'bg-[#F7931A]/10' : ''}
                                    ${(isCurrentMonth && !isSelectedStart && !isSelectedEnd) ? 'hover:bg-gray-800 rounded-md' : ''}
                                `}
                                onClick={() => handleDateClick(d)}
                                onMouseEnter={() => setHoverDate(d)}
                            >
                                {format(d, 'd')}
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    };

    return (
        <div className="relative font-sans" ref={containerRef}>
            {/* Input Trigger */}
            <div
                className={`
                    flex items-center gap-2 px-3 py-2 bg-[#1c1c1c] rounded-lg border w-72 transition-all relative
                    ${isOpen ? 'border-[#F7931A] ring-1 ring-[#F7931A]/30' : 'border-gray-800 hover:border-gray-600'}
                `}
            >
                <svg className="w-4 h-4 text-gray-400 min-w-[16px]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>

                <input
                    type="text"
                    value={inputValue}
                    onChange={handleInputChange}
                    onClick={() => !isOpen && setIsOpen(true)}
                    placeholder="YYYY-MM-DD ~ YYYY-MM-DD"
                    className="bg-transparent border-none outline-none text-sm text-gray-200 w-full placeholder-gray-600 font-sans"
                />

                {/* Clear Button */}
                {(startDate || inputValue) && (
                    <div
                        className="p-0.5 hover:bg-gray-700 rounded-full cursor-pointer"
                        onClick={(e) => {
                            e.stopPropagation();
                            onChange('', '');
                            setTempStart(null);
                            setTempEnd(null);
                            setInputValue('');
                        }}
                    >
                        <svg className="w-3 h-3 text-gray-500 hover:text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </div>
                )}
            </div>

            {/* Dropdown Content */}
            {isOpen && (
                <div className="absolute top-full left-0 mt-2 bg-[#1A1A1A] border border-gray-800 rounded-xl shadow-2xl z-50 flex overflow-hidden animate-in fade-in zoom-in-95 duration-100">

                    {/* Sidebar */}
                    <div className="w-32 border-r border-gray-800 p-2 flex flex-col gap-1 bg-[#141414]">
                        {(
                            [
                                { label: 'Today', id: 'today' },
                                { label: 'Yesterday', id: 'yesterday' },
                                { label: 'Last 7 days', id: 'last7' },
                                { label: 'Last 30 days', id: 'last30' },
                                { label: 'This Month', id: 'thisMonth' },
                                { label: 'Last Month', id: 'lastMonth' },
                                { label: 'Last 2 Years', id: 'last2Year' },
                                { label: 'Last 3 Years', id: 'last3Year' },
                                { label: 'Last 5 Years', id: 'last5Year' },
                                { label: 'Last 10 Years', id: 'last10Year' },
                                { label: 'Last 12 Years', id: 'last12Year' },
                            ] as const
                        ).map((preset) => (
                            <button
                                key={preset.id}
                                onClick={() => selectPreset(preset.id)}
                                className="text-left px-3 py-2 text-xs text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors"
                            >
                                {preset.label}
                            </button>
                        ))}
                    </div>

                    {/* Main Content */}
                    <div className="flex flex-col">
                        <div className="flex items-start border-b border-gray-800 relative">
                            {/* Previous Month (Only if left is in Days mode) */}
                            {leftViewMode === 'days' && (
                                <button
                                    onClick={() => setViewDate(subMonths(viewDate, 1))}
                                    className="absolute left-2 top-4 p-1 hover:bg-gray-800 rounded-full text-gray-400 hover:text-white z-20"
                                >
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                                    </svg>
                                </button>
                            )}

                            {/* Left Pane Block */}
                            <div className="border-r border-gray-800">
                                {leftViewMode === 'days' && renderCalendarDays(viewDate, true)}
                                {leftViewMode === 'months' && renderMonths(viewDate, 'left')}
                                {leftViewMode === 'years' && renderYears(viewDate, 'left')}
                            </div>

                            {/* Right Pane Block */}
                            <div>
                                {rightViewMode === 'days' && renderCalendarDays(addMonths(viewDate, 1), false)}
                                {rightViewMode === 'months' && renderMonths(addMonths(viewDate, 1), 'right')}
                                {rightViewMode === 'years' && renderYears(addMonths(viewDate, 1), 'right')}
                            </div>

                            {/* Next Month (Only if right is in Days mode) */}
                            {rightViewMode === 'days' && (
                                <button
                                    onClick={() => setViewDate(addMonths(viewDate, 1))}
                                    className="absolute right-2 top-4 p-1 hover:bg-gray-800 rounded-full text-gray-400 hover:text-white z-20"
                                >
                                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                    </svg>
                                </button>
                            )}
                        </div>

                        {/* Footer */}
                        <div className="flex items-center justify-end p-3 gap-2 bg-[#1A1A1A]">
                            <button
                                onClick={handleCancel}
                                className="px-4 py-2 text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleApply}
                                disabled={!tempStart || !tempEnd}
                                className={`
                                    px-4 py-2 text-xs font-bold text-black rounded-md transition-all
                                    ${(tempStart && tempEnd)
                                        ? 'bg-[#F7931A] hover:bg-[#e08618] shadow-lg shadow-orange-900/20'
                                        : 'bg-gray-700 cursor-not-allowed opacity-50'}
                                `}
                            >
                                Apply
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DateRangePicker;
