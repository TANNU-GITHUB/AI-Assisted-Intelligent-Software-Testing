'use client';

import { useState, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'motion/react';
import { Footer } from '@/components/navigation/Footer';
import { LabButton } from '@/components/ui/LabButton';
import {
  RotateCcw,
  Code2,
  FileText,
  Cpu,
  CheckCircle2,
  Loader2,
  Zap,
} from 'lucide-react';
import {
  checkHealth,
  createSession,
  fetchExample,
  persistSessionId,
  runCodeAnalysis,
  runRequirementAnalysis,
  type FunctionAnalysis,
  type SessionPayload,
  type StructuredRequirement,
} from '@/lib/api';

const TestingLabScene = dynamic(
  () => import('@/components/3d/TestingLabScene').then((m) => m.TestingLabScene),
  { ssr: false }
);

const FALLBACK_SOURCE = `def calculate_discount(price: float, is_member: bool) -> float:
    if price < 0:
        raise ValueError("price must be non-negative")
    if is_member:
        return price * 0.9
    return price


def checkout_total(prices: list[float], is_member: bool) -> float:
    total = 0.0
    for price in prices:
        total += calculate_discount(price, is_member)
    if total > 500 and is_member:
        total -= 20
    return total
`;

const FALLBACK_REQUIREMENTS = `Members receive a 10% discount on every item.
Non-members pay the full price.
Negative prices must be rejected with an error.
If a member's checkout total is greater than 500, apply an extra 20 currency units off.
Empty carts should produce a total of 0.
`;

const analysisStages = [
  { label: 'Saving source and requirements...', icon: FileText },
  { label: 'Analyzing source code...', icon: Code2 },
  { label: 'Analyzing requirements with Gemini...', icon: FileText },
];

export default function LiveLabPage() {
  const [phase, setPhase] = useState<'idle' | 'running' | 'complete'>('idle');
  const [stageIndex, setStageIndex] = useState(0);
  const [show3D, setShow3D] = useState(false);
  const [sourceCode, setSourceCode] = useState(FALLBACK_SOURCE);
  const [requirements, setRequirements] = useState(FALLBACK_REQUIREMENTS);
  const [filename, setFilename] = useState('sample_source.py');
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<SessionPayload | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setShow3D(true);
    checkHealth().then(setBackendUp);
    fetchExample()
      .then((example) => {
        setSourceCode(example.source_code);
        setRequirements(example.requirements_text);
        setFilename(example.filename);
      })
      .catch(() => undefined);
  }, []);

  const onUpload = (file: File) => {
    if (!file.name.toLowerCase().endsWith('.py')) {
      setError('Only Python source files (.py) are accepted.');
      return;
    }
    file.text().then((text) => {
      setSourceCode(text);
      setFilename(file.name);
      setError(null);
    });
  };

  const runAnalysis = async () => {
    setError(null);
    setSession(null);
    setPhase('running');
    setStageIndex(0);
    let latest: SessionPayload | null = null;
    try {
      const created = await createSession(sourceCode, requirements, filename);
      latest = created;
      persistSessionId(created.session_id);
      setStageIndex(1);
      const withCode = await runCodeAnalysis(created.session_id);
      latest = withCode;
      setSession(withCode);
      setStageIndex(2);
      const withReqs = await runRequirementAnalysis(created.session_id);
      latest = withReqs;
      persistSessionId(withReqs.session_id);
      setSession(withReqs);
      setStageIndex(3);
      setPhase('complete');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed.');
      if (latest) {
        setSession(latest);
        setPhase('complete');
      } else {
        setPhase('idle');
      }
    }
  };

  const reset = () => {
    setPhase('idle');
    setStageIndex(0);
    setError(null);
    setSession(null);
  };

  const functions: FunctionAnalysis[] = session?.code_analysis?.functions || [];
  const structuredReqs: StructuredRequirement[] =
    session?.requirement_analysis?.requirements || [];

  return (
    <>
      <section className="relative min-h-screen pt-20 px-4 sm:px-6 lg:px-10 pb-12">
        <div className="max-w-7xl mx-auto mb-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white">
                AI Testing Lab
              </h1>

            </div>
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-yellow-500/20 bg-yellow-500/5">
              <span
                className={`w-2 h-2 rounded-full ${
                  phase === 'running'
                    ? 'bg-yellow-500 animate-pulse'
                    : phase === 'complete'
                    ? 'bg-green-500'
                    : backendUp
                    ? 'bg-green-500'
                    : backendUp === false
                    ? 'bg-red-500'
                    : 'bg-neutral-600'
                }`}
              />
              <span className="font-mono text-xs text-yellow-500">
                {phase === 'idle' && (backendUp === false ? 'BACKEND OFFLINE' : 'READY')}
                {phase === 'running' && 'PROCESSING...'}
                {phase === 'complete' && 'COMPLETE'}
              </span>
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800 bg-neutral-900/50">
              <Code2 className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">SOURCE CODE</span>
              <span className="ml-auto text-xs text-neutral-600 font-mono">{filename}</span>
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                disabled={phase === 'running'}
                className="text-xs font-mono text-yellow-500 hover:text-yellow-400"
              >
                Upload
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".py"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onUpload(file);
                  e.target.value = '';
                }}
              />
            </div>
            <textarea
              value={sourceCode}
              onChange={(e) => setSourceCode(e.target.value)}
              disabled={phase === 'running'}
              spellCheck={false}
              className="w-full h-[400px] p-4 bg-transparent font-mono text-xs text-neutral-300 leading-relaxed resize-none outline-none scrollbar-hide"
            />
          </div>

          <div className="rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800 bg-neutral-900/50">
              <FileText className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">REQUIREMENTS</span>
              <span className="ml-auto text-xs text-neutral-600 font-mono">requirements.txt</span>
            </div>
            <textarea
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              disabled={phase === 'running'}
              spellCheck={false}
              className="w-full h-[400px] p-4 bg-transparent font-mono text-xs text-neutral-300 leading-relaxed resize-none outline-none scrollbar-hide"
            />
          </div>

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
              {phase === 'running' && (
                <div className="absolute bottom-4 left-4 right-4">
                  <div className="flex items-center gap-2 mb-2">
                    {(() => {
                      const StageIcon =
                        analysisStages[Math.min(stageIndex, analysisStages.length - 1)].icon;
                      return <StageIcon className="w-4 h-4 text-yellow-500 animate-pulse" />;
                    })()}
                    <span className="font-mono text-xs text-yellow-500">
                      {analysisStages[Math.min(stageIndex, analysisStages.length - 1)].label}
                    </span>
                  </div>
                  <div className="h-1 bg-neutral-800 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-yellow-500"
                      animate={{ width: `${((stageIndex + 1) / analysisStages.length) * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="max-w-7xl mx-auto mt-4 flex flex-col items-center justify-center gap-3">
          {error && (
            <p className="text-sm text-red-400 font-mono text-center max-w-2xl">{error}</p>
          )}
          {phase === 'idle' && (
            <LabButton size="lg" onClick={runAnalysis} disabled={backendUp === false}>
              <Zap className="w-4 h-4 fill-current" />
              Run Analysis
            </LabButton>
          )}
          {phase === 'running' && (
            <div className="flex items-center gap-2 px-4 py-3 rounded-lg border border-yellow-500/30 bg-yellow-500/5">
              <Loader2 className="w-4 h-4 text-yellow-500 animate-spin" />
              <span className="font-mono text-sm text-yellow-500">
                {analysisStages[Math.min(stageIndex, analysisStages.length - 1)].label}
              </span>
            </div>
          )}
          {phase === 'complete' && (
            <div className="flex items-center gap-4">
              <LabButton variant="secondary" size="sm" onClick={reset}>
                <RotateCcw className="w-4 h-4" />
                Reset
              </LabButton>
              {session?.session_id && (
                <a href={`/dashboard?session=${session.session_id}`}>
                  <LabButton size="sm">View Full Report</LabButton>
                </a>
              )}
            </div>
          )}
        </div>

        {functions.length > 0 && (
          <div className="max-w-7xl mx-auto mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white">Source Code Analysis</h3>
              <span className="flex items-center gap-1.5 text-green-500 text-sm">
                <CheckCircle2 className="w-4 h-4" />
                {functions.length} functions
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <AnimatePresence>
                {functions.map((fn) => (
                  <motion.div
                    key={fn.qualified_name}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 rounded-xl border border-yellow-500/20 bg-yellow-500/5"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs text-yellow-500">{fn.qualified_name}</span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-500">
                        CC {fn.cyclomatic_complexity}
                      </span>
                    </div>
                    <p className="text-sm text-white mb-2">
                      {fn.params.map((p) => p.name).join(', ') || 'no params'}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-neutral-500">
                      <span className="font-mono">lines {fn.lineno}–{fn.end_lineno}</span>
                      <span>•</span>
                      <span>{fn.branch_count} branches</span>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        )}

        {structuredReqs.length > 0 && (
          <div className="max-w-7xl mx-auto mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-white">Requirement Analysis</h3>
              <span className="flex items-center gap-1.5 text-green-500 text-sm">
                <CheckCircle2 className="w-4 h-4" />
                {structuredReqs.length} testable rules
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <AnimatePresence>
                {structuredReqs.map((req) => (
                  <motion.div
                    key={req.requirement_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 rounded-xl border border-green-500/20 bg-green-500/5"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs text-yellow-500">{req.requirement_id}</span>
                    </div>
                    <p className="text-sm text-white mb-2">{req.condition}</p>
                    <p className="text-xs text-neutral-400">{req.expected_result}</p>
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
