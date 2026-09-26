'use client';

import { useRef, useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion, useScroll, useTransform } from 'motion/react';
import { Footer } from '@/components/navigation/Footer';
import { LabButton } from '@/components/ui/LabButton';
import Link from 'next/link';
import {
  Code2,
  FileSearch,
  FileCode2,
  MonitorPlay,
  Bug,
  FileBarChart,
  ArrowRight,
} from 'lucide-react';

const TestingLabScene = dynamic(
  () => import('@/components/3d/TestingLabScene').then((m) => m.TestingLabScene),
  { ssr: false }
);

const stages = [
  {
    id: '01',
    name: 'SOURCE',
    title: 'Source Code Ingestion',
    description: 'The AI engine reads your source code, building a complete structural model of every function, branch, and dependency. Code fragments float through the environment as the system maps the architecture.',
    icon: Code2,
  },
  {
    id: '02',
    name: 'REQUIREMENTS',
    title: 'Requirement Analysis',
    description: 'Functional requirements are parsed and mapped to code paths. The AI identifies what needs testing and which code sections correspond to each requirement.',
    icon: FileSearch,
  },
  {
    id: '03',
    name: 'ANALYSIS',
    title: 'Deep Analysis',
    description: 'A yellow scanner passes through the code fragments, analyzing control flow, data dependencies, and potential edge cases. The system builds a comprehensive test model.',
    icon: FileSearch,
  },
  {
    id: '04',
    name: 'GENERATION',
    title: 'Test Case Generation',
    description: 'Test cards multiply as the AI generates comprehensive test cases across multiple testing strategies — White Box, Black Box, Unit, Integration, Regression, and Negative Testing.',
    icon: FileCode2,
  },
  {
    id: '05',
    name: 'EXECUTION',
    title: 'Parallel Execution',
    description: 'Browser windows appear as tests run simultaneously across simulated environments. Each test node moves through the pipeline: Queued → Running → Passed/Failed.',
    icon: MonitorPlay,
  },
  {
    id: '06',
    name: 'BUG DETECTION',
    title: 'Defect Detection',
    description: 'Black bug objects emerge from the environment. The scanning beam locks onto each defect, freezing it and displaying its root cause, severity, and affected module.',
    icon: Bug,
  },
  {
    id: '07',
    name: 'RESULTS',
    title: 'Result Analysis',
    description: 'Everything collapses into a structured view. Passed tests turn green, failed tests turn red, and the system compiles coverage metrics and traceability data.',
    icon: FileBarChart,
  },
  {
    id: '08',
    name: 'REPORT',
    title: 'Report Assembly',
    description: 'A 3D report assembles from floating data fragments into a complete, actionable document with defect classification, coverage analysis, and full requirement traceability.',
    icon: FileBarChart,
  },
];

export default function HowItWorksPage() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [activeStage, setActiveStage] = useState(0);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end end'],
  });
  const sceneScale = useTransform(scrollYProgress, [0, 1], [1, 1.5]);
  const sceneOpacity = useTransform(scrollYProgress, [0, 0.8, 1], [1, 1, 0.3]);

  useEffect(() => {
    const onScroll = () => {
      const sections = document.querySelectorAll('[data-stage]');
      sections.forEach((section, i) => {
        const rect = section.getBoundingClientRect();
        if (rect.top < window.innerHeight * 0.5 && rect.bottom > window.innerHeight * 0.3) {
          setActiveStage(i);
        }
      });
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <>
      {/* Sticky 3D background */}
      <div className="sticky top-0 h-screen w-full overflow-hidden -z-10">
        <motion.div style={{ scale: sceneScale, opacity: sceneOpacity }} className="absolute inset-0">
          <TestingLabScene scrollProgress={scrollYProgress.get()} />
        </motion.div>
        <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-black/60" />
      </div>

      {/* Content overlay */}
      <div ref={containerRef} className="relative -mt-[100vh]">
        {/* Intro */}
        <section className="min-h-screen flex items-center justify-center px-6 sm:px-10 lg:px-20">
          <div className="max-w-3xl text-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 px-3 py-1.5 mb-6 border border-yellow-500/30 bg-yellow-500/5 rounded-full"
            >
              <span className="font-mono text-xs text-yellow-500 tracking-wider">THE JOURNEY</span>
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.1 }}
              className="text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-tight"
            >
              Inside The AI Testing Pipeline
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="mt-6 text-neutral-400 text-lg max-w-xl mx-auto"
            >
              Scroll through the complete journey — from raw source code to
              actionable defect reports. Each stage activates a new phase of
              the AI testing engine.
            </motion.p>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              className="mt-8 flex items-center justify-center gap-2 text-yellow-500"
            >
              <span className="font-mono text-xs tracking-widest">SCROLL TO BEGIN</span>
              <motion.div
                animate={{ y: [0, 6, 0] }}
                transition={{ repeat: Infinity, duration: 1.5 }}
              >
                ↓
              </motion.div>
            </motion.div>
          </div>
        </section>

        {/* Stage sections */}
        {stages.map((stage, i) => (
          <section
            key={stage.id}
            data-stage
            className="min-h-screen flex items-center px-6 sm:px-10 lg:px-20"
          >
            <div className={`max-w-6xl mx-auto w-full grid gap-8 ${i % 2 === 0 ? 'lg:grid-cols-[1fr_1fr]' : 'lg:grid-cols-[1fr_1fr]'}`}>
              <motion.div
                initial={{ opacity: 0, x: i % 2 === 0 ? -30 : 30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: '-100px' }}
                transition={{ duration: 0.6 }}
                className={i % 2 === 0 ? 'lg:order-1' : 'lg:order-2'}
              >
                <div className="flex items-center gap-3 mb-4">
                  <span className="font-mono text-5xl font-bold text-yellow-500/20">
                    {stage.id}
                  </span>
                  <div className="w-12 h-12 rounded-xl border border-yellow-500/30 bg-yellow-500/10 flex items-center justify-center">
                    <stage.icon className="w-6 h-6 text-yellow-500" />
                  </div>
                </div>
                <div className="font-mono text-xs text-yellow-500 tracking-widest mb-2">
                  STAGE {stage.id} — {stage.name}
                </div>
                <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
                  {stage.title}
                </h2>
                <p className="text-neutral-400 text-base sm:text-lg leading-relaxed">
                  {stage.description}
                </p>
              </motion.div>

              {/* Visual indicator */}
              <motion.div
                initial={{ opacity: 0 }}
                whileInView={{ opacity: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className={`flex items-center justify-center ${i % 2 === 0 ? 'lg:order-2' : 'lg:order-1'}`}
              >
                <div className="relative w-full max-w-sm aspect-square rounded-2xl border border-neutral-800 bg-gradient-to-b from-neutral-900/50 to-transparent overflow-hidden">
                  <div className="absolute inset-0 bg-grid-yellow opacity-20" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
                      className="w-32 h-32 rounded-full border-2 border-dashed border-yellow-500/30 flex items-center justify-center"
                    >
                      <stage.icon className="w-12 h-12 text-yellow-500/40" />
                    </motion.div>
                  </div>
                  {/* Progress dots */}
                  <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1.5">
                    {stages.map((_, j) => (
                      <div
                        key={j}
                        className={`w-1.5 h-1.5 rounded-full transition-colors ${
                          j === activeStage ? 'bg-yellow-500' : 'bg-neutral-700'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </motion.div>
            </div>
          </section>
        ))}

        {/* Final CTA */}
        <section className="min-h-screen flex items-center justify-center px-6">
          <div className="text-center max-w-2xl">
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="text-3xl sm:text-4xl font-bold text-white mb-6"
            >
              The Pipeline Is Complete.
            </motion.h2>
            <p className="text-neutral-400 mb-8">
              Now see it in action with real code input and live test generation.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/live-lab">
                <LabButton size="lg">
                  Enter The Live Lab
                  <ArrowRight className="w-4 h-4" />
                </LabButton>
              </Link>
              <Link href="/dashboard">
                <LabButton variant="secondary" size="lg">
                  View Dashboard
                </LabButton>
              </Link>
            </div>
          </div>
        </section>
      </div>

      <Footer />
    </>
  );
}
