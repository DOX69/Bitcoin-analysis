'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import AuthPreviewChart from '../../components/AuthPreviewChart';

export default function SignupPage() {
    const router = useRouter();
    const [formData, setFormData] = useState({
        email: '',
        password: '',
        confirmPassword: ''
    });

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value
        });
    };

    const handleSignup = async (e: React.FormEvent) => {
        e.preventDefault();
        // Simulate signup
        if (formData.email && formData.password) {
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
                                src="/logo_B_ai_bg_removed.png"
                                alt="Bitcoin Analytics Logo"
                                fill
                                className="object-cover"
                                priority
                            />
                        </div>
                    </div>

                    <div className="text-center md:text-left">
                        <h1 className="text-3xl font-bold tracking-tight text-white">
                            Create an account
                        </h1>
                        <p className="mt-2 text-sm text-secondary-gray">
                            Start your journey with Bitcoin Analytics today.
                        </p>
                    </div>

                    <form className="mt-8 space-y-6" onSubmit={handleSignup}>
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
                                    value={formData.email}
                                    onChange={handleChange}
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
                                    autoComplete="new-password"
                                    required
                                    value={formData.password}
                                    onChange={handleChange}
                                    className="mt-1 block w-full rounded-md border border-secondary-charcoal bg-secondary-black px-3 py-2 text-white placeholder-gray-500 focus:border-primary-orange focus:outline-none focus:ring-1 focus:ring-primary-orange sm:text-sm"
                                    placeholder="Create a password"
                                />
                            </div>

                            <div>
                                <label htmlFor="confirmPassword" className="block text-sm font-medium text-secondary-gray">
                                    Confirm Password
                                </label>
                                <input
                                    id="confirmPassword"
                                    name="confirmPassword"
                                    type="password"
                                    autoComplete="new-password"
                                    required
                                    value={formData.confirmPassword}
                                    onChange={handleChange}
                                    className="mt-1 block w-full rounded-md border border-secondary-charcoal bg-secondary-black px-3 py-2 text-white placeholder-gray-500 focus:border-primary-orange focus:outline-none focus:ring-1 focus:ring-primary-orange sm:text-sm"
                                    placeholder="Confirm your password"
                                />
                            </div>
                        </div>

                        <div>
                            <button
                                type="submit"
                                className="group relative flex w-full justify-center rounded-md bg-primary-orange px-4 py-2 text-sm font-semibold text-white hover:bg-primary-orange/90 focus:outline-none focus:ring-2 focus:ring-primary-orange focus:ring-offset-2 focus:ring-offset-gray-900"
                            >
                                Sign up
                            </button>
                        </div>
                    </form>

                    <p className="mt-2 text-center text-sm text-secondary-gray">
                        Already have an account?{' '}
                        <Link href="/login" className="font-medium text-primary-orange hover:text-primary-orange/80">
                            Sign in
                        </Link>
                    </p>
                </div>
            </div>

            {/* Right Section: Graph Preview (Reused) */}
            <div className="hidden md:flex md:w-1/2 bg-secondary-black relative overflow-hidden flex-col justify-center items-center p-12">
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-primary-orange/10 via-backgrounds-dark to-backgrounds-dark opacity-50 pointer-events-none"></div>
                <div className="z-10 w-full max-w-lg space-y-6">
                    <div className="text-center mb-8">
                        <h2 className="text-2xl font-bold text-white mb-2">Join the Community</h2>
                        <p className="text-secondary-gray">Access premium analytics and charts.</p>
                    </div>
                    <div className="h-64 scale-110">
                        <AuthPreviewChart />
                    </div>
                </div>
            </div>

            {/* Mobile Preview Fallback */}
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
