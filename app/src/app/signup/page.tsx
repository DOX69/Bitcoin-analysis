'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import AuthKPIs from '../../components/AuthKPIs';
import EnergyBeam from '../../components/landing/EnergyBeam';
import EnergyGraph from '../../components/landing/EnergyGraph';

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
        <div className="min-h-screen flex flex-col md:flex-row bg-primary-dark font-sans text-text-primary relative overflow-hidden">
            <EnergyBeam />
            <EnergyGraph />

            {/* Left Section: Auth Form */}
            <div className="w-full md:w-1/2 flex flex-col justify-center items-center p-8 relative z-10">
                <div className="w-full max-w-md bg-white/95 backdrop-blur-xl rounded-2xl shadow-2xl p-8 md:p-12 space-y-8 border border-white/20">
                    {/* Logo */}
                    <div className="flex justify-center">
                        <Link href="/" className="relative w-12 h-12 rounded-full overflow-hidden shadow-lg shadow-black/10 hover:shadow-orange-500/20 transition-all duration-300 hover:scale-110 cursor-pointer block">
                            <Image
                                src="/logo_B_ai_bg_removed.png"
                                alt="Bitcoin Analytics Logo"
                                fill
                                className="object-cover bg-black"
                                priority
                            />
                        </Link>
                    </div>

                    <div className="text-center">
                        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
                            Create an account
                        </h1>
                        <p className="mt-2 text-sm text-gray-600">
                            Start your journey with Bitcoin Analytics today.
                        </p>
                    </div>

                    <form className="mt-8 space-y-6" onSubmit={handleSignup}>
                        <div className="space-y-4">
                            <div>
                                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
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
                                    className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-primary-orange focus:outline-none focus:ring-1 focus:ring-primary-orange sm:text-sm shadow-sm transition-all duration-200"
                                    placeholder="Enter your email"
                                />
                            </div>

                            <div>
                                <label htmlFor="password" className="block text-sm font-medium text-gray-700">
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
                                    className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-primary-orange focus:outline-none focus:ring-1 focus:ring-primary-orange sm:text-sm shadow-sm transition-all duration-200"
                                    placeholder="Create a password"
                                />
                            </div>

                            <div>
                                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
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
                                    className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 placeholder-gray-400 focus:border-primary-orange focus:outline-none focus:ring-1 focus:ring-primary-orange sm:text-sm shadow-sm transition-all duration-200"
                                    placeholder="Confirm your password"
                                />
                            </div>
                        </div>

                        <div>
                            <button
                                type="submit"
                                className="group relative flex w-full justify-center rounded-md bg-primary-orange px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 focus:outline-none focus:ring-2 focus:ring-primary-orange focus:ring-offset-2 focus:ring-offset-gray-50 shadow-lg shadow-orange-500/20 transition-all duration-300 hover:scale-[1.02]"
                            >
                                Sign up
                            </button>
                        </div>
                    </form>

                    <p className="mt-2 text-center text-sm text-gray-600">
                        Already have an account?{' '}
                        <Link href="/login" className="font-medium text-primary-orange hover:text-orange-600">
                            Sign in
                        </Link>
                    </p>
                </div>
            </div>

            {/* Right Section: KPI Preview (Reused) */}
            <div className="hidden md:flex md:w-1/2 relative overflow-hidden flex-col justify-center items-center p-12 z-10">
                <div className="z-10 w-full max-w-lg space-y-6">
                    <div className="text-center mb-12">
                        <h2 className="text-3xl font-bold text-white mb-2 drop-shadow-md">Join the Community</h2>
                        <p className="text-gray-300 text-lg">Access premium analytics and charts.</p>
                    </div>
                    <div className="flex justify-center transform scale-110">
                        <AuthKPIs />
                    </div>
                </div>
            </div>

            {/* Mobile Preview Fallback */}
            <div className="md:hidden p-6 bg-white/95 backdrop-blur-sm z-10 border-t border-gray-200">
                <div className="mb-4">
                    <h3 className="text-gray-900 font-semibold mb-2">Market Overview</h3>
                    <div className="transform scale-90 origin-top">
                        <AuthKPIs />
                    </div>
                </div>
            </div>

        </div>
    );
}
