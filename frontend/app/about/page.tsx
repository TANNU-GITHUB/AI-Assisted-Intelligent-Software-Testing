'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'motion/react';
import { Footer } from '@/components/navigation/Footer';
import { SectionHeading } from '@/components/ui/SectionHeading';
import { Bug, Scan, Code2, FileText, FileCode2, MonitorPlay, FileBarChart, Cpu } from 'lucide-react';

const BugScanCanvas = dynamic(
  () => import('@/components/3d/BugScanCanvas').then((m) => m.BugScanCanvas),
  { ssr: false }
);

const team = [
  {
    name: 'Dr. Aris Chen',
    role: 'AI Testing Architect',
    description: 'Designs the neural test generation models. 12+ years in automated testing research.',
    id: 'ID-001',
  },
  {
    name: 'Maya Okonkwo',
    role: 'Lead Test Engineer',
    description: 'Architects the execution pipeline and browser simulation environments.',
    id: 'ID-002',
  },
  {
    name: 'Kai Nakamura',
    role: 'Defect Analysis Lead',
    description: 'Builds the defect classification and root-cause analysis systems.',
    id: 'ID-003',
  },
];

const methodology = [
  { icon: Code2, title: 'Code-First Analysis', description: 'We start by understanding the actual source code structure, not just requirements documents.' },
  { icon: FileText, title: 'Requirement Mapping', description: 'Every requirement is traced to specific code paths, ensuring nothing is left untested.' },
  { icon: FileCode2, title: 'Multi-Strategy Generation', description: 'Six testing strategies work in parallel: White Box, Black Box, Unit, Integration, Regression, and Negative.' },
  { icon: MonitorPlay, title: 'Parallel Execution', description: 'Tests run in simulated browser environments simultaneously, dramatically reducing test time.' },
  { icon: Bug, title: 'Intelligent Detection', description: 'Failures are classified by root cause, severity, and affected module — not just pass/fail.' },
  { icon: FileBarChart, title: 'Actionable Reporting', description: 'Reports include traceability matrices, coverage gaps, and prioritized defect lists.' },
];

export default function AboutPage() {
  const [scanProgress, setScanProgress] = useState(0);
  const [showBug, setShowBug] = useState(false);

  useEffect(() => {
    setShowBug(true);
    const interval = setInterval(() => {
      setScanProgress((p) => (p >= 100 ? 0 : p + 0.5));
    }, 30);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      {/* Hero: Inside The Testing Lab */}
      <section className="relative min-h-screen flex items-center px-6 sm:px-10 lg:px-20 pt-20 overflow-hidden">
        <div className="max-w-6xl mx-auto w-full">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-3 py-1.5 mb-6 border border-yellow-500/30 bg-yellow-500/5 rounded-full"
          >
            <span className="font-mono text-xs text-yellow-500 tracking-wider">INSIDE THE TESTING LAB</span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-tight max-w-3xl"
          >
            We Don't Just Find Bugs.
            <br />
            <span className="text-yellow-500">We Understand Them.</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            className="mt-6 text-neutral-400 text-lg max-w-xl"
          >
            BUG/AI is an AI-assisted testing platform built on the principle
            that understanding software is the first step to testing it.
          </motion.p>
        </div>

        {/* 3D Bug scan visual */}
        <div className="absolute right-0 top-0 bottom-0 w-1/2 hidden lg:block opacity-60">
          {showBug && (
            <div className="relative w-full h-full">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="relative">
                  <div className="w-64 h-64">
                    <BugScanCanvas detected={scanProgress > 50} speed={0.5} />
                  </div>
                  {/* Scan line */}
                  <motion.div
                    className="absolute left-0 right-0 h-px bg-yellow-500"
                    style={{ top: `${scanProgress}%` }}
                  />
                  <div className="absolute -inset-8 border border-yellow-500/20 rounded-3xl pointer-events-none" />
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Bug breakdown section */}
      <section className="relative py-24 px-6 sm:px-10 lg:px-20">
        <div className="max-w-5xl mx-auto">
          <SectionHeading
            label="THE PROCESS"
            title="How A Bug Becomes A Report"
            description="When the AI finds a defect, it doesn't just flag it — it dissects the bug into its components."
          />

          <div className="mt-16 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { icon: Bug, label: 'DETECT', desc: 'The scanner locks onto the defect' },
              { icon: Scan, label: 'ANALYZE', desc: 'Root cause and severity are determined' },
              { icon: Code2, label: 'TRACE', desc: 'Affected code paths are identified' },
              { icon: FileText, label: 'CLASSIFY', desc: 'Bug is categorized by type and module' },
              { icon: FileCode2, label: 'LINK', desc: 'Connected test cases and requirements' },
              { icon: FileBarChart, label: 'REPORT', desc: 'Assembled into actionable output' },
            ].map((step, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ delay: i * 0.1 }}
                className="group relative p-6 rounded-2xl border border-neutral-800 bg-gradient-to-b from-neutral-900/50 to-transparent hover:border-yellow-500/40 transition-colors"
              >
                <div className="w-10 h-10 rounded-xl bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center mb-4">
                  <step.icon className="w-5 h-5 text-yellow-500" />
                </div>
                <div className="font-mono text-xs text-yellow-500 tracking-wider mb-1">
                  STEP {String(i + 1).padStart(2, '0')} — {step.label}
                </div>
                <p className="text-sm text-neutral-400">{step.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Methodology */}
      <section className="relative py-24 px-6 sm:px-10 lg:px-20">
        <div className="max-w-5xl mx-auto">
          <SectionHeading
            label="METHODOLOGY"
            title="Our Testing Principles"
            description="Six core principles guide everything the AI testing engine does."
          />

          <div className="mt-16 space-y-4">
            {methodology.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ delay: i * 0.08 }}
                className="group flex items-start gap-6 p-6 rounded-2xl border border-neutral-800 bg-neutral-950 hover:bg-neutral-900/50 transition-colors"
              >
                <div className="w-12 h-12 rounded-xl bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                  <item.icon className="w-6 h-6 text-yellow-500" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white mb-1">{item.title}</h3>
                  <p className="text-neutral-400">{item.description}</p>
                </div>
                <div className="ml-auto font-mono text-3xl font-bold text-yellow-500/10">
                  {String(i + 1).padStart(2, '0')}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="relative py-24 px-6 sm:px-10 lg:px-20">
        <div className="max-w-5xl mx-auto">
          <SectionHeading
            label="THE TEAM"
            title="Inside The Lab"
            description="The engineers building the AI testing engine."
          />

          <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-4">
            {team.map((member, i) => (
              <motion.div
                key={member.id}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-50px' }}
                transition={{ delay: i * 0.1 }}
                whileHover={{ y: -4 }}
                className="group relative p-6 rounded-2xl border border-neutral-800 bg-gradient-to-b from-neutral-900/50 to-transparent hover:border-yellow-500/40 transition-colors overflow-hidden"
              >
                {/* Scanner effect */}
                <motion.div
                  className="absolute left-0 right-0 h-px bg-yellow-500/30"
                  animate={{ top: ['0%', '100%', '0%'] }}
                  transition={{ duration: 3, repeat: Infinity, delay: i * 0.5 }}
                />

                {/* Abstract 3D object placeholder */}
                <div className="relative w-24 h-24 mx-auto mb-4">
                  <motion.div
                    whileHover={{ rotateY: 180 }}
                    transition={{ duration: 0.6 }}
                    className="w-full h-full rounded-2xl border border-yellow-500/30 bg-gradient-to-br from-yellow-500/10 to-transparent flex items-center justify-center"
                    style={{ transformStyle: 'preserve-3d' }}
                  >
                    <Cpu className="w-10 h-10 text-yellow-500/60" />
                  </motion.div>
                </div>

                {/* ID card */}
                <div className="font-mono text-xs text-yellow-500/60 mb-2">{member.id}</div>
                <h3 className="text-lg font-bold text-white mb-1">{member.name}</h3>
                <div className="text-xs text-yellow-500 font-mono mb-3">{member.role}</div>
                <p className="text-sm text-neutral-400">{member.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </>
  );
}
