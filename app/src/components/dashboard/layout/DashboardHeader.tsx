'use client';

import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Badge } from '@/components/ui/badge';
import { buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface DashboardHeaderProps {
    currentPage?: string;
}

const navItems = [
    { name: 'Home', href: '/' },
    { name: 'Dashboard', href: '/dashboard' },
];

const DashboardHeader: React.FC<DashboardHeaderProps> = ({ currentPage = 'Dashboard' }) => {
    return (
        <header className="dashboard-header">
            <div className="flex min-h-16 items-center justify-between gap-3 px-4 py-2 md:px-6">
                <Link href="/" className="flex shrink-0 items-center gap-2" aria-label="B.ai home">
                        <Image
                            src="/logo_B_ai_bg_removed.png"
                            alt=""
                            width={38}
                            height={36}
                            className="rounded-lg"
                        />
                        <span className="text-lg font-semibold text-white">B.ai</span>
                </Link>

                <nav className="flex items-center gap-1" aria-label="Primary navigation">
                    {navItems.map((item) => (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                buttonVariants({ variant: 'ghost', size: 'sm' }),
                                'min-h-11 px-3',
                                currentPage === item.name && 'bg-primary/15 text-foreground ring-1 ring-primary/30',
                            )}
                        >
                            {item.name}
                        </Link>
                    ))}
                </nav>

                <Badge variant="outline" className="hidden min-h-8 border-primary/30 bg-primary/10 text-primary sm:inline-flex">
                    Read-only data
                </Badge>
            </div>
        </header>
    );
};

export default DashboardHeader;
