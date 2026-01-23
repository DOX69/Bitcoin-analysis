'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import AuthPreviewChart from '../../components/AuthPreviewChart';
import { theme } from '../../theme';

const DUMMY_CREDENTIALS = {
    email: 'test@example.com',
    password: 'test123',
};

export default function LoginPage() {
    const [email, setEmail] = useState(DUMMY_CREDENTIALS.email);
    const [password, setPassword] = useState(DUMMY_CREDENTIALS.password);
    const router = useRouter();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        // Simulate auth check
        if (email && password) {
            router.push('/dashboard');
        }
    };

    return (
        <div className="min-h-screen flex flex-col md:flex-row bg-primary-dark font-sans text-text-primary">
            {/* Left Section: Auth Form */}
            <div className="w-full md:w-1/2 flex flex-col justify-center items-center p-8 bg-backgrounds-dark relative z-10">
                <div className="w-full max-w-md space-y-8">
                    {/* Logo */}
                    <div className="flex justify-center md:justify-start">
                        <div className="relative w-12 h-12 rounded-full overflow-hidden">
                            <Image
                                src="/logo_B_ai.jpeg"
                                alt="Bitcoin Analytics Logo"
                                fill
                                className="object-cover"
                                priority
                            />
                        </div>
                    </div>

                    <div className="text-center md:text-left">
                        <h1 className="text-3xl font-bold tracking-tight text-white">
                            Sign in to Bitcoin Analytics
                        </h1>
                        <p className="mt-2 text-sm text-secondary-gray">
                            Welcome back! Please enter your details.
                        </p>
                    </div>

                    <form className="mt-8 space-y-6" onSubmit={handleLogin}>
                        <div className="space-y-4">
                            <div>
                                <label htmlFor="email" className="block text-sm font-medium text-secondary-gray">
                                    Email
                                </label>
                                <input
                                    id="email"
                                    name="email"
                                    type="email"
                                    autoComplete="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="mt-1 block w-full rounded-md border border-secondary-charcoal bg-secondary-black px-3 py-2 text-white placeholder-gray-500 focus:border-primary-orange focus:outline-none focus:ring-1 focus:ring-primary-orange sm:text-sm"
                                    placeholder="Enter your email"
                                />
                            </div>

                            <div>
                                <label htmlFor="password" className="block text-sm font-medium text-secondary-gray">
                                    Password
                                </label>
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    autoComplete="current-password"
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="mt-1 block w-full rounded-md border border-secondary-charcoal bg-secondary-black px-3 py-2 text-white placeholder-gray-500 focus:border-primary-orange focus:outline-none focus:ring-1 focus:ring-primary-orange sm:text-sm"
                                    placeholder="Enter your password"
                                />
                            </div>
                        </div>

                        <div className="flex items-center justify-between">
                            <div className="flex items-center">
                                <input
                                    id="remember-me"
                                    name="remember-me"
                                    type="checkbox"
                                    className="h-4 w-4 rounded border-gray-300 text-primary-orange focus:ring-primary-orange"
                                />
                                <label htmlFor="remember-me" className="ml-2 block text-sm text-secondary-gray">
                                    Remember me
                                </label>
                            </div>

                            <div className="text-sm">
                                <a href="#" className="font-medium text-primary-orange hover:text-primary-orange/80">
                                    Forgot password?
                                </a>
                            </div>
                        </div>

                        <div>
                            <button
                                type="submit"
                                className="group relative flex w-full justify-center rounded-md bg-primary-orange px-4 py-2 text-sm font-semibold text-white hover:bg-primary-orange/90 focus:outline-none focus:ring-2 focus:ring-primary-orange focus:ring-offset-2 focus:ring-offset-gray-900"
                            >
                                Sign in
                            </button>
                        </div>
                    </form>

                    <p className="mt-2 text-center text-sm text-secondary-gray">
                        Don&apos;t have an account?{' '}
                        <Link href="/signup" className="font-medium text-primary-orange hover:text-primary-orange/80">
                            Sign up
                        </Link>
                    </p>
                </div>
            </div>

            {/* Right Section: Graph Preview */}
            <div className="hidden md:flex md:w-1/2 bg-secondary-black relative overflow-hidden flex-col justify-center items-center p-12">
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary-orange/10 via-backgrounds-dark to-backgrounds-dark opacity-50 pointer-events-none"></div>

                <div className="z-10 w-full max-w-lg space-y-6">
                    <div className="text-center mb-8">
                        <h2 className="text-2xl font-bold text-white mb-2">Market Insights at a Glance</h2>
                        <p className="text-secondary-gray">Get real-time analytics immediately upon login.</p>
                    </div>

                    <div className="grid grid-cols-1 gap-4">
                        <div className="h-48">
                            <AuthPreviewChart />
                        </div>
                        {/* Visual balance: maybe a smaller secondary chart or stats row could go here, 
                    but sticking to one main preview chart for clarity as per design reqs '2-3 mini charts' - let's add a placeholder for a second one to match '2-3' req */}
                        <div className="h-32 opacity-70 scale-95 origin-top">
                            <AuthPreviewChart />
                        </div>
                    </div>

                    <div className="flex justify-center gap-4 mt-8">
                        <div className="px-3 py-1 rounded-full bg-secondary-charcoal border border-secondary-charcoal/50 text-xs text-secondary-gray">Valid Signals</div>
                        <div className="px-3 py-1 rounded-full bg-secondary-charcoal border border-secondary-charcoal/50 text-xs text-secondary-gray">Real-time Data</div>
                    </div>
                </div>
            </div>

            {/* Mobile Footer/Preview Section fallback - simplified for mobile */}
            <div className="md:hidden p-6 bg-secondary-black">
                <div className="mb-4">
                    <h3 className="text-white font-semibold mb-2">Preview</h3>
                    <div className="h-40">
                        <AuthPreviewChart />
                    </div>
                </div>
            </div>

        </div>
    );
}
