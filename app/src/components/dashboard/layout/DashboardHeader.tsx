'use client';

import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { Bell, ChevronDown, Settings } from 'lucide-react';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button, buttonVariants } from '@/components/ui/button';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuGroup,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';

interface DashboardHeaderProps {
    currentPage?: string;
}

const navItems = [
    { name: 'Dashboard', href: '/dashboard' },
    { name: 'Screener', href: '/screener' },
    { name: 'Terminal', href: '/terminal' },
    { name: 'Stats', href: '/stats' },
    { name: 'FAQ', href: '/faq' },
];

const DashboardHeader: React.FC<DashboardHeaderProps> = ({ currentPage = 'Dashboard' }) => {
    return (
        <header className="dashboard-header">
            <div className="flex items-center justify-between px-6 py-3">
                <div className="flex items-center gap-8">
                    <Link href="/" className="flex items-center gap-2">
                        <Image
                            src="/logo_B_ai_bg_removed.png"
                            alt="B.ai Logo"
                            width={36}
                            height={36}
                            className="rounded-lg"
                        />
                        <span className="text-lg font-semibold text-white">B.ai</span>
                    </Link>

                    <nav className="hidden items-center gap-1 md:flex">
                        {navItems.map((item) => (
                            <Link
                                key={item.name}
                                href={item.href}
                                className={cn(
                                    buttonVariants({ variant: 'ghost', size: 'sm' }),
                                    currentPage === item.name && 'bg-primary/15 text-foreground ring-1 ring-primary/30',
                                )}
                            >
                                {item.name}
                            </Link>
                        ))}
                    </nav>
                </div>

                <div className="flex items-center gap-4">
                    <Badge variant="secondary" className="hidden gap-2 border-success/30 bg-success/10 text-success sm:inline-flex">
                        <span className="size-2 rounded-full bg-success" />
                        Connected
                    </Badge>

                    <div className="flex items-center gap-2">
                        <Button variant="ghost" size="icon" aria-label="Settings">
                            <Settings />
                        </Button>
                        <Button variant="ghost" size="icon" aria-label="Notifications">
                            <Bell />
                        </Button>
                    </div>

                    <DropdownMenu>
                        <DropdownMenuTrigger
                            render={<Button variant="ghost" className="h-auto gap-2 p-1" />}
                        >
                            <Avatar>
                                <AvatarFallback className="bg-gradient-to-br from-energy-orange to-energy-yellow text-black">U</AvatarFallback>
                            </Avatar>
                            <span className="hidden text-left sm:block">
                                <span className="block text-sm font-medium text-white">User</span>
                                <span className="block text-xs text-gray-400">0x50f9...a7b845a5</span>
                            </span>
                            <ChevronDown className="text-gray-400" />
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-48">
                            <DropdownMenuGroup>
                                <DropdownMenuItem render={<Link href="/profile" />}>Profile</DropdownMenuItem>
                                <DropdownMenuItem render={<Link href="/settings" />}>Settings</DropdownMenuItem>
                            </DropdownMenuGroup>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem variant="destructive" render={<Link href="/" />}>Logout</DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </div>
        </header>
    );
};

export default DashboardHeader;
