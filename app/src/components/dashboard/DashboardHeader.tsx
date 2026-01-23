'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';

interface DashboardHeaderProps {
    currentPage?: string;
}

const navItems = [
    { name: 'Dashboard', href: '/dashboard', active: true },
    { name: 'Screener', href: '/screener' },
    { name: 'Terminal', href: '/terminal' },
    { name: 'Stats', href: '/stats' },
    { name: 'FAQ', href: '/faq' },
];

const DashboardHeader: React.FC<DashboardHeaderProps> = ({ currentPage = 'Dashboard' }) => {
    const [isProfileOpen, setIsProfileOpen] = useState(false);

    return (
        <header className="dashboard-header">
            <div className="flex items-center justify-between px-6 py-3">
                {/* Logo Section */}
                <div className="flex items-center gap-8">
                    <Link href="/" className="flex items-center gap-2">
                        <Image
                            src="/logo_B_ai.jpeg"
                            alt="B.ai Logo"
                            width={36}
                            height={36}
                            className="rounded-lg"
                        />
                        <span className="text-lg font-semibold text-white">B.ai</span>
                    </Link>

                    {/* Navigation */}
                    <nav className="hidden md:flex items-center gap-1">
                        {navItems.map((item) => (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={`nav-link ${currentPage === item.name ? 'nav-link-active' : ''}`}
                            >
                                {item.name}
                            </Link>
                        ))}
                    </nav>
                </div>

                {/* Right Section */}
                <div className="flex items-center gap-4">
                    {/* Connection Status */}
                    <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-green-500/10 border border-green-500/30">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs text-green-400 font-medium">Connected</span>
                    </div>

                    {/* Action Icons */}
                    <div className="flex items-center gap-2">
                        <button className="header-icon-btn" aria-label="Settings">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                        </button>
                        <button className="header-icon-btn" aria-label="Notifications">
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                            </svg>
                        </button>
                    </div>

                    {/* User Profile */}
                    <div className="relative">
                        <button
                            onClick={() => setIsProfileOpen(!isProfileOpen)}
                            className="flex items-center gap-2 p-1 rounded-lg hover:bg-white/5 smooth-transition"
                        >
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-energy-orange to-energy-yellow flex items-center justify-center">
                                <span className="text-sm font-bold text-black">U</span>
                            </div>
                            <div className="hidden sm:block text-left">
                                <div className="text-sm font-medium text-white">User</div>
                                <div className="text-xs text-gray-400">0x50f9...a7b845a5</div>
                            </div>
                            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </button>

                        {/* Dropdown Menu */}
                        {isProfileOpen && (
                            <div className="absolute right-0 mt-2 w-48 rounded-lg bg-gray-900 border border-gray-700 shadow-xl z-50">
                                <div className="py-1">
                                    <Link href="/profile" className="block px-4 py-2 text-sm text-gray-300 hover:bg-gray-800">
                                        Profile
                                    </Link>
                                    <Link href="/settings" className="block px-4 py-2 text-sm text-gray-300 hover:bg-gray-800">
                                        Settings
                                    </Link>
                                    <hr className="my-1 border-gray-700" />
                                    <button className="block w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-gray-800">
                                        Logout
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </header>
    );
};

export default DashboardHeader;
