'use client';

import { useRef, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'motion/react';
import Link from 'next/link';
import { ArrowRight, Play, Zap, Bug as BugIcon, ScanLine } from 'lucide-react';
import { LabButton } from '@/components/ui/LabButton';

const TestingLabScene = dynamic(
  () => import('@/components/3d/TestingLabScene').then((m) => m.TestingLabScene),
  { ssr: false, loading: () => <SceneLoader /> }
);

function SceneLoader() {
  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-12 h-12 border-2 border-yellow-500/30 border-t-yellow-500 rounded-full animate-spin" />
        <span className="font-mono text-xs text-yellow-500/60 animate-pulse">
          INITIALIZING TESTING LAB...
        </span>
      </div>
    </div>
  );
}

export function Hero() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    const onScroll = () => {
      const max = window.innerHeight;
      setScrollProgress(Math.min(window.scrollY / max, 1));
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <section
      ref={containerRef}
      className="relative min-h-screen w-full overflow-hidden"
    >
      {/* 3D Scene - full background */}
      <div className="absolute inset-0 z-0">
        {mounted && <TestingLabScene scrollProgress={scrollProgress} />}
      </div>

      {/* Gradient overlay — uses background color so it matches the theme */}
      <div className="absolute inset-0 z-10 bg-gradient-to-r from-background via-background/60 to-transparent pointer-events-none" />
      <div className="absolute inset-0 z-10 bg-gradient-to-t from-background via-transparent to-background/40 pointer-events-none" />

      {/* Content */}
      <div className="relative z-20 min-h-screen flex items-center px-6 sm:px-10 lg:px-20">
        <div className="max-w-2xl">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-3 py-1.5 mb-6 border border-yellow-500/30 bg-yellow-500/5 rounded-full"
          >
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-yellow-500 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-yellow-500" />
            </span>
            <span className="font-mono text-xs text-yellow-500 tracking-wider">
              AI TESTING ENGINE ONLINE
            </span>
          </motion.div>

          {/* Title */}
          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight text-foreground leading-[1.05]"
          >
            Find Bugs
            <br />
            <span className="relative">
              <span className="text-stroke-yellow">Before</span>{' '}
              <span className="text-yellow-500">Your Users</span>
            </span>
            <br />
            Do.
          </motion.h1>

          {/* Description */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="mt-6 text-base sm:text-lg text-muted-foreground max-w-xl leading-relaxed"
          >
            AI-assisted software testing that analyzes requirements, understands
            source code, generates test cases, executes them, and turns
            failures into actionable reports.
          </motion.p>

          {/* Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="mt-8 flex flex-col sm:flex-row gap-4"
          >
            <Link href="/live-lab">
              <LabButton size="lg" className="w-full sm:w-auto">
                <Play className="w-4 h-4 fill-current" />
                Run Live Simulation
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </LabButton>
            </Link>
            <Link href="/how-it-works">
              <LabButton variant="secondary" size="lg" className="w-full sm:w-auto">
                <ScanLine className="w-4 h-4" />
                Explore The Testing Lab
              </LabButton>
            </Link>
          </motion.div>

          {/* Stats bar */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.7 }}
            className="mt-12 flex items-center gap-6 sm:gap-8"
          >
            {[
              { icon: BugIcon, label: 'Defects Found', value: '47' },
              { icon: Zap, label: 'Test Cases', value: '1,284' },
              { icon: ScanLine, label: 'Coverage', value: '95%' },
            ].map((stat, i) => (
              <div key={i} className="flex items-center gap-3">
                <stat.icon className="w-4 h-4 text-yellow-500/60" />
                <div>
                  <div className="text-xl font-bold text-foreground">{stat.value}</div>
                  <div className="text-xs text-muted-foreground font-mono uppercase tracking-wider">
                    {stat.label}
                  </div>
                </div>
                {i < 2 && <div className="w-px h-8 bg-border" />}
              </div>
            ))}
          </motion.div>
        </div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2"
      >
        <span className="font-mono text-xs text-neutral-500 tracking-widest">SCROLL TO EXPLORE</span>
        <motion.div
          animate={{ y: [0, 8, 0] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
          className="w-px h-8 bg-gradient-to-b from-yellow-500 to-transparent"
        />
      </motion.div>
    </section>
  );
}
