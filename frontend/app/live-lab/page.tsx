'use client';

import { useState, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'motion/react';
import { Footer } from '@/components/navigation/Footer';
import { LabButton } from '@/components/ui/LabButton';
import {
  Play,
  RotateCcw,
  Code2,
  FileText,
  Cpu,
  CheckCircle2,
  XCircle,
  Loader2,
  Scan,
  Bug,
  FileBarChart,
  Zap,
} from 'lucide-react';

const TestingLabScene = dynamic(
  () => import('@/components/3d/TestingLabScene').then((m) => m.TestingLabScene),
  { ssr: false }
);

const simulationStages = [
  { label: 'Reading source code...', icon: Code2, duration: 1500 },
  { label: 'Analyzing requirements...', icon: FileText, duration: 1500 },
  { label: 'Building test model...', icon: Cpu, duration: 1500 },
  { label: 'Generating test cases...', icon: FileText, duration: 2000 },
  { label: 'Executing tests...', icon: Play, duration: 2000 },
  { label: 'Scanning for defects...', icon: Scan, duration: 1500 },
  { label: 'Analyzing failures...', icon: Bug, duration: 1500 },
  { label: 'Generating report...', icon: FileBarChart, duration: 1500 },
];

const mockTestCases = [
  { id: 'TC-001', name: 'Valid login with correct credentials', type: 'Unit', status: 'passed', module: 'Auth' },
  { id: 'TC-002', name: 'Login with invalid password', type: 'Negative', status: 'passed', module: 'Auth' },
  { id: 'TC-003', name: 'Session timeout after inactivity', type: 'Integration', status: 'failed', module: 'Session' },
  { id: 'TC-004', name: 'Concurrent user registration', type: 'Integration', status: 'passed', module: 'User' },
  { id: 'TC-005', name: 'SQL injection in search field', type: 'Negative', status: 'passed', module: 'Search' },
  { id: 'TC-006', name: 'Password reset flow', type: 'Regression', status: 'failed', module: 'Auth' },
  { id: 'TC-007', name: 'API rate limiting enforcement', type: 'Integration', status: 'passed', module: 'API' },
  { id: 'TC-008', name: 'File upload size validation', type: 'Unit', status: 'passed', module: 'Upload' },
  { id: 'TC-009', name: 'Role-based access control', type: 'White Box', status: 'passed', module: 'Auth' },
  { id: 'TC-010', name: 'Data integrity on network failure', type: 'Negative', status: 'failed', module: 'Network' },
  { id: 'TC-011', name: 'Cache invalidation on update', type: 'Regression', status: 'passed', module: 'Cache' },
  { id: 'TC-012', name: 'Pagination with 1000+ records', type: 'Black Box', status: 'passed', module: 'Data' },
];

const sourceCode = `function authenticate(email, password) {
  const user = db.findUser(email);
  if (!user) return { error: 'User not found' };
  
  const valid = bcrypt.compare(password, user.hash);
  if (!valid) return { error: 'Invalid credentials' };
  
  const session = createSession(user.id);
  return { session, user };
}

function createSession(userId) {
  return {
    id: uuid(),
    userId,
    expires: Date.now() + 3600000,
  };
}`;

const requirements = `REQ-01: User shall be able to login with email and password
REQ-02: System shall reject invalid credentials
REQ-03: Sessions shall expire after 1 hour
REQ-04: Password reset shall require email verification
REQ-05: API shall enforce rate limiting (100 req/min)
REQ-06: File uploads shall be limited to 10MB
REQ-07: Role-based access shall restrict admin endpoints
REQ-08: System shall handle network failures gracefully`;

export default function LiveLabPage() {
  const [phase, setPhase] = useState<'idle' | 'running' | 'complete'>('idle');
  const [stageIndex, setStageIndex] = useState(0);
  const [visibleTests, setVisibleTests] = useState(0);
  const [show3D, setShow3D] = useState(false);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    setShow3D(true);
  }, []);

  const runSimulation = () => {
    setPhase('running');
    setStageIndex(0);
    setVisibleTests(0);
    timersRef.current.forEach(clearTimeout);
    timersRef.current = [];

    let elapsed = 0;
    simulationStages.forEach((stage, i) => {
      elapsed += stage.duration;
      timersRef.current.push(
        setTimeout(() => {
          setStageIndex(i + 1);
          if (i === 3) {
            // Start revealing test cases
            mockTestCases.forEach((_, j) => {
              timersRef.current.push(
                setTimeout(() => setVisibleTests(j + 1), j * 150)
              );
            });
          }
          if (i === simulationStages.length - 1) {
            timersRef.current.push(
              setTimeout(() => setPhase('complete'), 500)
            );
          }
        }, elapsed)
      );
    });
  };

  const reset = () => {
    timersRef.current.forEach(clearTimeout);
    setPhase('idle');
    setStageIndex(0);
    setVisibleTests(0);
  };

  useEffect(() => {
    return () => timersRef.current.forEach(clearTimeout);
  }, []);

  const passed = mockTestCases.filter((t) => t.status === 'passed').length;
  const failed = mockTestCases.filter((t) => t.status === 'failed').length;

  return (
    <>
      <section className="relative min-h-screen pt-20 px-4 sm:px-6 lg:px-10 pb-12">
        {/* Header */}
        <div className="max-w-7xl mx-auto mb-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white">
                AI Testing Lab
              </h1>
              <p className="text-sm text-neutral-500 mt-1">
                Interactive simulation workspace — frontend demo with mock data
              </p>
            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-yellow-500/20 bg-yellow-500/5">
              <span className={`w-2 h-2 rounded-full ${
                phase === 'running' ? 'bg-yellow-500 animate-pulse' :
                phase === 'complete' ? 'bg-green-500' : 'bg-neutral-600'
              }`} />
              <span className="font-mono text-xs text-yellow-500">
                {phase === 'idle' && 'READY'}
                {phase === 'running' && 'PROCESSING...'}
                {phase === 'complete' && 'COMPLETE'}
              </span>
            </div>
          </div>
        </div>

        {/* Main grid */}
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Source Code Panel */}
          <div className="rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800 bg-neutral-900/50">
              <Code2 className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">SOURCE CODE</span>
              <span className="ml-auto text-xs text-neutral-600 font-mono">auth.js</span>
            </div>
            <div className="p-4 max-h-[400px] overflow-auto scrollbar-hide">
              <pre className="font-mono text-xs text-neutral-300 leading-relaxed">
                <code>{sourceCode.split('\n').map((line, i) => (
                  <div key={i} className="flex">
                    <span className="text-neutral-600 w-6 select-none">{i + 1}</span>
                    <span className={line.trim().startsWith('function') ? 'text-yellow-500' : ''}>
                      {line || ' '}
                    </span>
                  </div>
                ))}</code>
              </pre>
            </div>
          </div>

          {/* Requirements Panel */}
          <div className="rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800 bg-neutral-900/50">
              <FileText className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">REQUIREMENTS</span>
              <span className="ml-auto text-xs text-neutral-600 font-mono">spec.md</span>
            </div>
            <div className="p-4 max-h-[400px] overflow-auto scrollbar-hide space-y-2">
              {requirements.split('\n').map((line, i) => (
                <div key={i} className="flex items-start gap-2 text-xs">
                  <span className="text-yellow-500 font-mono">{line.split(':')[0]}</span>
                  <span className="text-neutral-400">{line.split(':')[1]}</span>
                </div>
              ))}
            </div>
          </div>

          {/* AI Engine Panel */}
          <div className="rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800 bg-neutral-900/50">
              <Cpu className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">AI ENGINE</span>
            </div>
            <div className="relative h-[400px]">
              {show3D && (
                <div className="absolute inset-0">
                  <TestingLabScene scrollProgress={phase === 'running' ? 0.5 : 0} />
                </div>
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-neutral-950 via-transparent to-transparent" />
              {/* Stage overlay */}
              {phase === 'running' && (
                <div className="absolute bottom-4 left-4 right-4">
                  <div className="flex items-center gap-2 mb-2">
                    {(() => {
                      const StageIcon = simulationStages[Math.min(stageIndex, simulationStages.length - 1)].icon;
                      return <StageIcon className="w-4 h-4 text-yellow-500 animate-pulse" />;
                    })()}
                    <span className="font-mono text-xs text-yellow-500">
                      {simulationStages[Math.min(stageIndex, simulationStages.length - 1)].label}
                    </span>
                  </div>
                  <div className="h-1 bg-neutral-800 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-yellow-500"
                      animate={{ width: `${(stageIndex / simulationStages.length) * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Control bar */}
        <div className="max-w-7xl mx-auto mt-4 flex items-center justify-center gap-4">
          {phase === 'idle' && (
            <LabButton size="lg" onClick={runSimulation}>
              <Zap className="w-4 h-4 fill-current" />
              Generate Tests
            </LabButton>
          )}
          {phase === 'running' && (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-4 py-3 rounded-lg border border-yellow-500/30 bg-yellow-500/5">
                <Loader2 className="w-4 h-4 text-yellow-500 animate-spin" />
                <span className="font-mono text-sm text-yellow-500">
                  {simulationStages[Math.min(stageIndex, simulationStages.length - 1)].label}
                </span>
              </div>
            </div>
          )}
          {phase === 'complete' && (
            <div className="flex items-center gap-4">
              <LabButton variant="secondary" size="sm" onClick={reset}>
                <RotateCcw className="w-4 h-4" />
                Reset
              </LabButton>
              <a href="/dashboard">
                <LabButton size="sm">
                  View Full Report
                </LabButton>
              </a>
            </div>
          )}
        </div>

        {/* Generated test cases */}
        {(phase === 'running' || phase === 'complete') && visibleTests > 0 && (
          <div className="max-w-7xl mx-auto mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white">Generated Test Cases</h3>
              {phase === 'complete' && (
                <div className="flex items-center gap-4 text-sm">
                  <span className="flex items-center gap-1.5 text-green-500">
                    <CheckCircle2 className="w-4 h-4" />
                    {passed} Passed
                  </span>
                  <span className="flex items-center gap-1.5 text-red-500">
                    <XCircle className="w-4 h-4" />
                    {failed} Failed
                  </span>
                </div>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <AnimatePresence>
                {mockTestCases.slice(0, visibleTests).map((tc, i) => (
                  <motion.div
                    key={tc.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className={`p-4 rounded-xl border ${
                      tc.status === 'passed' ? 'border-green-500/20 bg-green-500/5' :
                      tc.status === 'failed' ? 'border-red-500/20 bg-red-500/5' :
                      'border-neutral-800 bg-neutral-900/50'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs text-yellow-500">{tc.id}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        tc.status === 'passed' ? 'bg-green-500/10 text-green-500' :
                        'bg-red-500/10 text-red-500'
                      }`}>
                        {tc.status === 'passed' ? 'PASSED' : 'FAILED'}
                      </span>
                    </div>
                    <p className="text-sm text-white mb-2">{tc.name}</p>
                    <div className="flex items-center gap-2 text-xs text-neutral-500">
                      <span className="font-mono">{tc.type}</span>
                      <span>•</span>
                      <span>{tc.module}</span>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        )}
      </section>

      <Footer />
    </>
  );
}
