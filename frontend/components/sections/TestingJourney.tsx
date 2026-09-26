'use client';

import { useRef, useState, useEffect } from 'react';
import { motion, useInView, AnimatePresence } from 'motion/react';
import { SectionHeading } from '@/components/ui/SectionHeading';
import {
  Code2,
  FileSearch,
  FileCode2,
  MonitorPlay,
  Bug,
  FileBarChart,
  ArrowRight,
} from 'lucide-react';

const stages = [
  {
    id: '01',
    name: 'SOURCE',
    title: 'Source Code',
    description: 'AI ingests your source code, building a structural model of every function, branch, and dependency.',
    icon: Code2,
    color: '#FACC15',
  },
  {
    id: '02',
    name: 'ANALYZE',
    title: 'Requirement Analysis',
    description: 'Functional requirements are parsed and mapped to code paths, identifying what needs testing.',
    icon: FileSearch,
    color: '#FACC15',
  },
  {
    id: '03',
    name: 'GENERATE',
    title: 'Test Generation',
    description: 'The AI engine generates comprehensive test cases across multiple testing strategies.',
    icon: FileCode2,
    color: '#FACC15',
  },
  {
    id: '04',
    name: 'EXECUTE',
    title: 'Execution',
    description: 'Tests run simultaneously across simulated browser environments and execution nodes.',
    icon: MonitorPlay,
    color: '#FACC15',
  },
  {
    id: '05',
    name: 'DETECT',
    title: 'Bug Detection',
    description: 'Failures are analyzed, root causes identified, and defects are classified by severity.',
    icon: Bug,
    color: '#EF4444',
  },
  {
    id: '06',
    name: 'REPORT',
    title: 'Reporting',
    description: 'Coverage metrics, traceability matrices, and actionable defect reports are assembled.',
    icon: FileBarChart,
    color: '#22C55E',
  },
];

export function TestingJourney() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '-100px' });
  const [activeStage, setActiveStage] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const interval = setInterval(() => {
      setActiveStage((prev) => (prev + 1) % stages.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [inView]);

  return (
    <section ref={ref} className="relative py-24 sm:py-32 px-6 sm:px-10 lg:px-20">
      <SectionHeading
        label="THE PIPELINE"
        title="From Source Code to Actionable Report"
        description="Watch how raw code transforms through a multi-stage AI testing pipeline into comprehensive defect reports."
      />

      {/* Pipeline visual */}
      <div className="mt-16 max-w-6xl mx-auto">
        {/* Desktop: horizontal conveyor */}
        <div className="hidden md:block relative">
          {/* Track line */}
          <div className="absolute top-12 left-0 right-0 h-px bg-border" />
          <motion.div
            className="absolute top-12 left-0 h-px bg-yellow-500"
            initial={{ width: '0%' }}
            animate={inView ? { width: `${((activeStage + 1) / stages.length) * 100}%` } : {}}
            transition={{ duration: 0.5 }}
            style={{ boxShadow: '0 0 10px rgba(250,204,21,0.5)' }}
          />

          <div className="grid grid-cols-6 gap-2">
            {stages.map((stage, i) => (
              <div
                key={stage.id}
                className="relative flex flex-col items-center"
                onMouseEnter={() => setActiveStage(i)}
              >
                {/* Module node */}
                <motion.div
                  animate={{
                    scale: activeStage === i ? 1.1 : 1,
                    y: activeStage === i ? -4 : 0,
                  }}
                  transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                  className={`relative w-24 h-24 rounded-2xl border flex items-center justify-center transition-colors ${
                    activeStage === i
                      ? 'border-yellow-500 bg-yellow-500/10'
                      : i < activeStage
                      ? 'border-yellow-500/30 bg-yellow-500/5'
                      : 'border-border bg-card/50'
                  }`}
                >
                  <stage.icon
                    className={`w-8 h-8 transition-colors ${
                      activeStage === i ? 'text-yellow-500' : 'text-muted-foreground'
                    }`}
                  />
                  {/* Module number */}
                  <span className="absolute -top-2 -right-2 text-[10px] font-mono font-bold w-5 h-5 rounded-full bg-yellow-500 text-black flex items-center justify-center">
                    {stage.id}
                  </span>
                  {/* Active glow */}
                  {activeStage === i && (
                    <motion.div
                      layoutId="stage-glow"
                      className="absolute inset-0 rounded-2xl border border-yellow-500/50"
                      style={{ boxShadow: '0 0 20px rgba(250,204,21,0.2)' }}
                    />
                  )}
                </motion.div>

                {/* Label */}
                <div className="mt-4 text-center">
                  <div className={`font-mono text-xs tracking-wider transition-colors ${
                    activeStage === i ? 'text-yellow-500' : 'text-neutral-500'
                  }`}>
                    {stage.name}
                  </div>
                  <div className="text-sm text-foreground mt-1">{stage.title}</div>
                </div>

                {/* Arrow */}
                {i < stages.length - 1 && (
                  <ArrowRight className="absolute top-10 -right-3 w-4 h-4 text-muted-foreground" />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Mobile: vertical list */}
        <div className="md:hidden space-y-4">
          {stages.map((stage, i) => (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, x: -20 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ delay: i * 0.1 }}
              className={`flex items-center gap-4 p-4 rounded-xl border ${
                activeStage === i ? 'border-yellow-500 bg-yellow-500/5' : 'border-border'
              }`}
              onClick={() => setActiveStage(i)}
            >
              <div className="w-12 h-12 rounded-lg border border-border bg-card flex items-center justify-center flex-shrink-0">
                <stage.icon className="w-5 h-5 text-yellow-500" />
              </div>
              <div>
                <div className="font-mono text-xs text-yellow-500">{stage.name}</div>
                <div className="text-sm text-foreground">{stage.title}</div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Active stage detail */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeStage}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.3 }}
            className="mt-12 max-w-2xl mx-auto p-6 rounded-2xl border border-yellow-500/20 bg-gradient-to-b from-yellow-500/5 to-transparent"
          >
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-xl bg-yellow-500/10 border border-yellow-500/30 flex items-center justify-center flex-shrink-0">
                {(() => {
                  const Icon = stages[activeStage].icon;
                  return <Icon className="w-6 h-6 text-yellow-500" />;
                })()}
              </div>
              <div>
                <div className="font-mono text-xs text-yellow-500 tracking-wider mb-1">
                  MODULE {stages[activeStage].id} — {stages[activeStage].name}
                </div>
                <h3 className="text-xl font-bold text-foreground mb-2">
                  {stages[activeStage].title}
                </h3>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  {stages[activeStage].description}
                </p>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}
