'use client';

import { useRef, useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { SectionHeading } from '@/components/ui/SectionHeading';
import {
  Scan,
  GitBranch,
  MonitorPlay,
  Target,
  Link2,
  FileBarChart,
  X,
} from 'lucide-react';

const features = [
  {
    id: 'analysis',
    title: 'AI-Powered Analysis',
    description: 'A scanner moves across your source code, building a complete model of internal logic, control flow, and data dependencies.',
    icon: Scan,
    visual: 'scanner',
    details: ['Control flow mapping', 'Branch identification', 'Data flow analysis', 'Dependency tracking'],
  },
  {
    id: 'dual',
    title: 'Dual Testing Strategy',
    description: 'Tests split into White Box and Black Box streams simultaneously, covering both internal logic and external behavior.',
    icon: GitBranch,
    visual: 'split',
    details: ['White Box: internal logic', 'Black Box: external behavior', 'Parallel execution', 'Combined coverage'],
  },
  {
    id: 'execution',
    title: 'Automated Execution',
    description: 'Mini browser windows run test cases in parallel, simulating real user interactions and edge cases.',
    icon: MonitorPlay,
    visual: 'browsers',
    details: ['Parallel test runs', 'Browser simulation', 'Edge case testing', 'Real-time monitoring'],
  },
  {
    id: 'coverage',
    title: 'Coverage Tracking',
    description: 'A 3D coverage sphere visualizes exactly which code paths are tested and which remain uncovered.',
    icon: Target,
    visual: 'sphere',
    details: ['Path coverage', 'Branch coverage', 'Function coverage', 'Gap identification'],
  },
  {
    id: 'traceability',
    title: 'Requirement Traceability',
    description: 'Every requirement connects visually to its generated tests, execution results, and coverage data.',
    icon: Link2,
    visual: 'graph',
    details: ['Requirement → Test mapping', 'Coverage gaps', 'Impact analysis', 'Audit trail'],
  },
  {
    id: 'reports',
    title: 'Instant Reports',
    description: 'Reports assemble from floating data fragments into a structured, actionable document with full traceability.',
    icon: FileBarChart,
    visual: 'report',
    details: ['Defect classification', 'Severity ranking', 'Coverage metrics', 'Traceability matrix'],
  },
];

export function FeatureLab() {
  const [activeFeature, setActiveFeature] = useState<string | null>(null);
  const active = features.find((f) => f.id === activeFeature);

  return (
    <section className="relative py-24 sm:py-32 px-6 sm:px-10 lg:px-20">
      <SectionHeading
        label="CAPABILITIES"
        title="The Testing Workstation"
        description="Six interconnected modules form a complete AI testing laboratory — from code analysis to defect reporting."
      />

      <div className="mt-16 max-w-6xl mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {features.map((feature, i) => (
          <motion.div
            key={feature.id}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: '-50px' }}
            transition={{ duration: 0.5, delay: i * 0.08 }}
            whileHover={{ y: -4 }}
            onClick={() => setActiveFeature(feature.id)}
            data-cursor="open"
            className="group relative p-6 rounded-2xl border border-border bg-gradient-to-b from-card/50 to-transparent hover:border-yellow-500/40 transition-colors cursor-pointer overflow-hidden"
          >
            {/* Hover scanner effect */}
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity">
              <div className="absolute inset-0 bg-gradient-to-b from-yellow-500/5 to-transparent" />
              <motion.div
                className="absolute left-0 right-0 h-px bg-yellow-500/50"
                initial={{ top: '0%' }}
                animate={{ top: ['0%', '100%', '0%'] }}
                transition={{ duration: 3, repeat: Infinity }}
              />
            </div>

            <div className="relative z-10">
              {/* Icon */}
              <div className="w-12 h-12 rounded-xl bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <feature.icon className="w-6 h-6 text-yellow-500" />
              </div>

              <h3 className="text-lg font-bold text-foreground mb-2">{feature.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>

              {/* Visual indicator */}
              <div className="mt-4 flex items-center gap-2 text-xs font-mono text-yellow-500/60 group-hover:text-yellow-500 transition-colors">
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-pulse" />
                <span>MODULE_{String(i + 1).padStart(2, '0')}</span>
                <span className="ml-auto group-hover:translate-x-1 transition-transform">→</span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Detail modal */}
      <AnimatePresence>
        {active && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] flex items-center justify-center p-6 bg-black/80 backdrop-blur-sm"
            onClick={() => setActiveFeature(null)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              onClick={(e) => e.stopPropagation()}
              className="relative max-w-lg w-full p-8 rounded-2xl border border-yellow-500/30 bg-gradient-to-b from-card to-background"
            >
              <button
                onClick={() => setActiveFeature(null)}
                className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="w-16 h-16 rounded-2xl bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center mb-6">
                <active.icon className="w-8 h-8 text-yellow-500" />
              </div>

              <h3 className="text-2xl font-bold text-foreground mb-3">{active.title}</h3>
              <p className="text-muted-foreground mb-6">{active.description}</p>

              <div className="space-y-2">
                {active.details.map((detail, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 * i }}
                    className="flex items-center gap-3 p-3 rounded-lg bg-card/50 border border-border"
                  >
                    <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                    <span className="text-sm text-foreground">{detail}</span>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}
