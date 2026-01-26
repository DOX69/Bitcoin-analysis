'use client';

import Header from '@/components/landing/Header';
import Hero from '@/components/landing/Hero';
import Features from '@/components/landing/Features';
import Footer from '@/components/landing/Footer';
import EnergyBeam from '@/components/landing/EnergyBeam';
import EnergyGraph from '@/components/landing/EnergyGraph';

export default function Home() {
  return (
    <main className="relative min-h-screen bg-black overflow-hidden selection:bg-orange-500/30">
      {/* Background Ambience */}
      <EnergyBeam />
      <EnergyGraph />

      {/* Header Navigation */}
      <Header />

      {/* Content */}
      <Hero />

      {/* Features Section */}
      <Features />

      {/* Footer */}
      <Footer />
    </main>
  );
}
