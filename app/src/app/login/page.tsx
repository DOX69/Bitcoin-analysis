'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AuthKPIs } from '@/components/dashboard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import EnergyBeam from '../../components/landing/EnergyBeam';
import EnergyGraph from '../../components/landing/EnergyGraph';

const DUMMY_CREDENTIALS = {
    email: 'example@email.com',
    password: 'test123',
};

export default function LoginPage() {
    const [email, setEmail] = useState(DUMMY_CREDENTIALS.email);
    const [password, setPassword] = useState(DUMMY_CREDENTIALS.password);
    const router = useRouter();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        if (email && password) {
            router.push('/dashboard');
        }
    };

    return (
        <div className="relative flex min-h-screen flex-col overflow-hidden bg-background font-sans text-foreground md:flex-row">
            <EnergyBeam />
            <EnergyGraph />

            <div className="relative z-10 flex w-full flex-col items-center justify-center p-8 transition-colors duration-500 md:w-1/2">
                <Card className="w-full max-w-md border-white/20 bg-white/95 px-8 py-8 text-gray-900 shadow-2xl backdrop-blur-xl md:px-12 md:py-12">
                    <CardHeader className="items-center gap-6 p-0 text-center">
                        <Link
                            href="/"
                            className="relative block size-12 overflow-hidden rounded-full shadow-lg transition-all duration-300 hover:scale-110"
                        >
                            <Image
                                src="/logo_B_ai_bg_removed.png"
                                alt="Bitcoin Analytics Logo"
                                fill
                                className="bg-black object-cover"
                                priority
                            />
                        </Link>
                        <div className="flex flex-col gap-2">
                            <h1 className="text-3xl font-bold tracking-tight">
                                Sign in to Bitcoin Analytics
                            </h1>
                            <p className="text-sm text-gray-600">
                                Welcome back! Please enter your details.
                            </p>
                        </div>
                    </CardHeader>

                    <CardContent className="p-0 pt-8">
                        <form className="flex flex-col gap-6" onSubmit={handleLogin}>
                            <FieldGroup>
                                <Field>
                                    <FieldLabel htmlFor="email">Email</FieldLabel>
                                    <Input
                                        id="email"
                                        name="email"
                                        type="email"
                                        autoComplete="email"
                                        required
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        placeholder="Enter your email"
                                        className="bg-white text-gray-900"
                                    />
                                </Field>
                                <Field>
                                    <FieldLabel htmlFor="password">Password</FieldLabel>
                                    <Input
                                        id="password"
                                        name="password"
                                        type="password"
                                        autoComplete="current-password"
                                        required
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        placeholder="Enter your password"
                                        className="bg-white text-gray-900"
                                    />
                                </Field>
                            </FieldGroup>

                            <div className="flex items-center justify-between gap-4">
                                <Field orientation="horizontal" className="w-auto items-center">
                                    <Checkbox id="remember-me" name="remember-me" />
                                    <FieldLabel htmlFor="remember-me" className="font-normal text-gray-600">
                                        Remember me
                                    </FieldLabel>
                                </Field>
                                <a href="#" className="text-sm font-medium text-primary-orange hover:text-orange-600">
                                    Forgot password?
                                </a>
                            </div>

                            <Button type="submit" className="w-full shadow-lg shadow-orange-500/20">
                                Sign in
                            </Button>
                        </form>
                    </CardContent>

                    <CardFooter className="justify-center gap-1 border-0 bg-transparent p-0 pt-2 text-sm text-gray-600">
                        Don&apos;t have an account?{' '}
                        <Link href="/signup" className="font-medium text-primary-orange hover:text-orange-600">
                            Sign up
                        </Link>
                    </CardFooter>
                </Card>
            </div>

            <div className="relative z-10 hidden w-1/2 flex-col items-center justify-center overflow-hidden p-12 md:flex">
                <div className="z-10 flex w-full max-w-lg flex-col gap-6">
                    <div className="mb-12 text-center">
                        <h2 className="mb-2 text-3xl font-bold text-white drop-shadow-md">Real-Time Market Data</h2>
                        <p className="text-lg text-gray-300">Instant access to key Bitcoin metrics and analytics.</p>
                    </div>
                    <div className="flex justify-center scale-110">
                        <AuthKPIs />
                    </div>
                    <div className="mt-12 flex justify-center gap-4">
                        <span className="rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm text-gray-300 backdrop-blur-md">Live Updates</span>
                        <span className="rounded-full border border-white/20 bg-white/10 px-4 py-1.5 text-sm text-gray-300 backdrop-blur-md">Institutional Grade</span>
                    </div>
                </div>
            </div>

            <div className="relative z-10 border-t border-gray-200 bg-white/95 p-6 backdrop-blur-sm md:hidden">
                <h3 className="mb-2 font-semibold text-gray-900">Market Overview</h3>
                <div className="origin-top scale-90">
                    <AuthKPIs />
                </div>
            </div>
        </div>
    );
}
