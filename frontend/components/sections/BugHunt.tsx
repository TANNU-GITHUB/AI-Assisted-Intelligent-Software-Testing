'use client';

import { useRef, useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'motion/react';
import { SectionHeading } from '@/components/ui/SectionHeading';
import { LabButton } from '@/components/ui/LabButton';
import { Scan, Bug, AlertTriangle, Crosshair } from 'lucide-react';

const BugHuntScene = dynamic(
  () => import('@/components/3d/BugHuntScene').then((m) => m.BugHuntScene),
  { ssr: false }
);

export function BugHunt() {
  const [phase, setPhase] = useState<'idle' | 'scanning' | 'detected' | 'found'>('idle');
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (phase !== 'scanning') return;
    const interval = setInterval(() => {
      setProgress((p) => {
        if (p >= 100) {
          setPhase('detected');
          return 100;
        }
        return p + 2;
      });
    }, 40);
    return () => clearInterval(interval);
  }, [phase]);

  useEffect(() => {
    if (phase === 'detected') {
      const timer = setTimeout(() => setPhase('found'), 1500);
      return () => clearTimeout(timer);
    }
  }, [phase]);

  return (
    <section className="relative py-24 sm:py-32 px-6 sm:px-10 lg:px-20">
      <SectionHeading
        label="INTERACTIVE"
        title="Find The Bug"
        description="Inspect the miniature application environment. The AI scanner identifies hidden defects in real-time."
      />

      <div className="mt-16 max-w-5xl mx-auto">
        <div className="relative rounded-3xl border border-border overflow-hidden bg-background aspect-[16/10]">
          {/* 3D Scene */}
          <div className="absolute inset-0">
            <BugHuntScene active={phase === 'scanning' || phase === 'detected'} />
          </div>

          {/* HUD overlay */}
          <div className="absolute inset-0 pointer-events-none">
            {/* Corner brackets */}
            {[
              'top-4 left-4 border-l-2 border-t-2',
              'top-4 right-4 border-r-2 border-t-2',
              'bottom-4 left-4 border-l-2 border-b-2',
              'bottom-4 right-4 border-r-2 border-b-2',
            ].map((cls, i) => (
              <div key={i} className={`absolute w-8 h-8 ${cls} border-yellow-500/40`} />
            ))}

            {/* Status */}
            <div className="absolute top-6 left-1/2 -translate-x-1/2 flex items-center gap-2 px-4 py-2 rounded-full bg-background/60 backdrop-blur border border-yellow-500/20">
              <span className={`w-2 h-2 rounded-full ${
                phase === 'idle' ? 'bg-neutral-600' :
                phase === 'scanning' ? 'bg-yellow-500 animate-pulse' :
                phase === 'detected' ? 'bg-yellow-500' :
                'bg-red-500'
              }`} />
              <span className="font-mono text-xs text-yellow-500 tracking-wider">
                {phase === 'idle' && 'READY TO SCAN'}
                {phase === 'scanning' && `SCANNING... ${progress}%`}
                {phase === 'detected' && 'DEFECT DETECTED'}
                {phase === 'found' && 'BUG FOUND'}
              </span>
            </div>

            {/* Scanning progress bar */}
            {phase === 'scanning' && (
              <div className="absolute bottom-8 left-8 right-8">
                <div className="h-1 bg-neutral-800 rounded-full overflow-hidden">
                  <motion.div
                    className="h-full bg-yellow-500"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            {/* Bug detection result */}
            <AnimatePresence>
              {phase === 'found' && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="absolute inset-0 flex items-center justify-center bg-background/60 backdrop-blur-sm"
                >
                  <motion.div
                    initial={{ y: 20 }}
                    animate={{ y: 0 }}
                    className="relative p-6 rounded-2xl border border-red-500/40 bg-gradient-to-b from-card to-background max-w-sm"
                  >
                    <div className="flex items-center gap-2 mb-4">
                      <Crosshair className="w-5 h-5 text-red-500" />
                      <span className="font-mono text-sm font-bold text-red-500 tracking-wider">
                        BUG FOUND
                      </span>
                    </div>

                    <div className="space-y-3">
                      <div>
                        <div className="text-xs font-mono text-muted-foreground uppercase">Description</div>
                        <div className="text-sm text-foreground">Authentication state mismatch</div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <div className="text-xs font-mono text-neutral-500 uppercase">Severity</div>
                          <div className="flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3 text-red-500" />
                            <span className="text-sm text-red-500 font-bold">HIGH</span>
                          </div>
                        </div>
                        <div>
                          <div className="text-xs font-mono text-neutral-500 uppercase">Module</div>
                          <div className="text-sm text-foreground">Login</div>
                        </div>
                        <div>
                          <div className="text-xs font-mono text-neutral-500 uppercase">Test Case</div>
                          <div className="text-sm text-yellow-500 font-mono">TC-047</div>
                        </div>
                        <div>
                          <div className="text-xs font-mono text-neutral-500 uppercase">Bug ID</div>
                          <div className="text-sm text-yellow-500 font-mono">BUG-042</div>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Action button */}
            {phase === 'idle' && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="pointer-events-auto" data-cursor="open">
                  <LabButton
                    size="lg"
                    onClick={() => {
                      setProgress(0);
                      setPhase('scanning');
                    }}
                  >
                    <Scan className="w-4 h-4" />
                    Start AI Scan
                  </LabButton>
                </div>
              </div>
            )}

            {phase === 'found' && (
              <div className="absolute bottom-6 left-1/2 -translate-x-1/2 pointer-events-auto">
                <LabButton
                  variant="secondary"
                  size="sm"
                  onClick={() => setPhase('idle')}
                >
                  Scan Again
                </LabButton>
              </div>
            )}
          </div>
        </div>

        {/* Info strip */}
        <div className="mt-6 grid grid-cols-3 gap-4">
          {[
            { label: 'Components Scanned', value: '12' },
            { label: 'Suspicious Patterns', value: '3' },
            { label: 'Defects Found', value: '1' },
          ].map((stat, i) => (
            <div key={i} className="p-4 rounded-xl border border-border bg-card/30">
              <div className="text-2xl font-bold text-yellow-500">{stat.value}</div>
              <div className="text-xs font-mono text-muted-foreground uppercase tracking-wider">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
