'use client';

import { useState, useRef, useEffect } from 'react';
import dynamic from 'next/dynamic';
import { motion, AnimatePresence } from 'motion/react';
import { Footer } from '@/components/navigation/Footer';
import { LabButton } from '@/components/ui/LabButton';
import { GitHubPicker } from '@/components/github/GitHubPicker';
import {
  RotateCcw,
  Code2,
  FileText,
  Cpu,
  GitBranch,
  CheckCircle2,
  Loader2,
  Zap,
  XCircle,
  ImageIcon,
} from 'lucide-react';
import {
  checkHealth,
  createSession,
  extractRequirementsDocument,
  extractRequirementsDiagram,
  persistSessionId,
  runCodeAnalysis,
  runRequirementAnalysis,
  runWhiteBoxTests,
  runBlackBoxTests,
  runGrayBoxTests,
  runOtherTests,
  runExecuteTests,
  runCoverage,
  runGapFillTests,
  type FunctionAnalysis,
  type SessionPayload,
  type StructuredRequirement,
} from '@/lib/api';

const TestingLabScene = dynamic(
  () => import('@/components/3d/TestingLabScene').then((m) => m.TestingLabScene),
  { ssr: false }
);

const analysisStages = [
  { label: 'Saving source and requirements...', icon: FileText },
  { label: 'Analyzing source code...', icon: Code2 },
  { label: 'Analyzing requirements with LLM...', icon: FileText },
  { label: 'Generating white-box tests...', icon: Code2 },
  { label: 'Generating black-box tests...', icon: FileText },
  { label: 'Generating gray-box tests...', icon: GitBranch },
  { label: 'Generating integration & negative tests...', icon: FileText },
  { label: 'Executing generated tests...', icon: Cpu },
  { label: 'Measuring coverage...', icon: Cpu },
  { label: 'Filling uncovered lines and requirements...', icon: FileText },
];

export default function LiveLabPage() {
  const [phase, setPhase] = useState<'idle' | 'running' | 'complete'>('idle');
  const [stageIndex, setStageIndex] = useState(0);
  const [show3D, setShow3D] = useState(false);
  const [sourceCode, setSourceCode] = useState('');
  const [requirements, setRequirements] = useState('');
  const [filename, setFilename] = useState('');
  const [backendUp, setBackendUp] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [requirementsFilename, setRequirementsFilename] = useState('');
  const [requirementsInputType, setRequirementsInputType] = useState<
    'text' | 'pdf' | 'document' | 'diagram'
  >('text');
  const [extractingRequirements, setExtractingRequirements] = useState(false);
  const [diagramPreview, setDiagramPreview] = useState<string | null>(null);
  const [extractingDiagram, setExtractingDiagram] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const requirementsFileRef = useRef<HTMLInputElement>(null);
  const diagramFileRef = useRef<HTMLInputElement>(null);
  const runningRef = useRef(false);

  useEffect(() => {
    setShow3D(true);
    checkHealth().then(setBackendUp);
  }, []);

  useEffect(() => {
    return () => {
      if (diagramPreview) URL.revokeObjectURL(diagramPreview);
    };
  }, [diagramPreview]);

  const onRequirementsUpload = async (file: File, uploadType: 'pdf' | 'document') => {
    const name = file.name.toLowerCase();
    const allowed = uploadType === 'pdf'
      ? ['.pdf']
      : ['.doc', '.docx', '.txt', '.md'];
    if (!allowed.some((ext) => name.endsWith(ext))) {
      setError(
        uploadType === 'pdf'
          ? 'Choose a PDF requirements file.'
          : 'Requirements documents must be Word (.doc / .docx) or text (.txt / .md) files.'
      );
      return;
    }
    setExtractingRequirements(true);
    setError(null);
    try {
      const extracted = await extractRequirementsDocument(file);
      setRequirements(extracted.requirements_text);
      setRequirementsFilename(file.name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not read that requirements file.');
    } finally {
      setExtractingRequirements(false);
    }
  };

  const onDiagramUpload = async (file: File) => {
    const name = file.name.toLowerCase();
    const allowed = ['.png', '.jpg', '.jpeg', '.gif', '.webp'];
    if (!allowed.some((ext) => name.endsWith(ext))) {
      setError('Diagrams must be PNG, JPEG, GIF, or WEBP images.');
      return;
    }
    // Show local preview immediately
    const previewUrl = URL.createObjectURL(file);
    setDiagramPreview(previewUrl);
    setRequirementsFilename(file.name);
    setExtractingDiagram(true);
    setError(null);
    try {
      const result = await extractRequirementsDiagram(file);
      setRequirements((prev) => {
        const existing = prev.trim();
        const newText = result.requirements_text.trim();
        return existing ? `${existing}\n${newText}` : newText;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not extract requirements from diagram.');
    } finally {
      setExtractingDiagram(false);
    }
  };

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
    if (runningRef.current) return;
    if (!sourceCode.trim() || !requirements.trim()) {
      setError('Please enter or upload both Python source code and requirements.');
      return;
    }
    runningRef.current = true;
    let latest: SessionPayload | null = null;
    try {
      setError(null);
      setSession(null);
      setPhase('running');
      setStageIndex(0);
      const created = await createSession(sourceCode, requirements, filename || 'source.py');
      latest = created;
      persistSessionId(created.session_id);
      setStageIndex(1);
      const withCode = await runCodeAnalysis(created.session_id);
      latest = withCode;
      setSession(withCode);
      setStageIndex(2);
      const withReqs = await runRequirementAnalysis(created.session_id);
      latest = withReqs;
      setSession(withReqs);
      setStageIndex(3);
      try {
        const withWhiteBox = await runWhiteBoxTests(created.session_id);
        latest = withWhiteBox;
        setSession(withWhiteBox);
      } catch (wbErr) {
        console.warn('White-box test generation notice:', wbErr);
      }
      setStageIndex(4);

      try {
        const withBlackBox = await runBlackBoxTests(created.session_id);
        latest = withBlackBox;
        setSession(withBlackBox);
      } catch (bbErr) {
        console.warn('Black-box test generation notice:', bbErr);
      }
      setStageIndex(5);
      try {
        const withGrayBox = await runGrayBoxTests(created.session_id);
        latest = withGrayBox;
        setSession(withGrayBox);
      } catch (gbErr) {
        console.warn('Gray-box test generation notice:', gbErr);
      }
      setStageIndex(6);

      try {
        const withOther = await runOtherTests(created.session_id);
        latest = withOther;
        setSession(withOther);
      } catch (otherErr) {
        setError(
          otherErr instanceof Error
            ? `Other tests skipped: ${otherErr.message}`
            : 'Other tests skipped.'
        );
      }
      setStageIndex(7);

      try {
        const executed = await runExecuteTests(created.session_id);
        latest = executed;
        setSession(executed);
      } catch (execErr) {
        console.warn('Test execution notice:', execErr);
      }
      setStageIndex(8);

      let covered = latest;
      try {
        covered = await runCoverage(created.session_id);
        latest = covered;
        setSession(covered);
      } catch (covErr) {
        console.warn('Coverage notice:', covErr);
      }
      setStageIndex(8);

      const missing = covered?.coverage?.missing_lines?.length || 0;
      const untested = covered?.requirement_coverage?.untested_count || 0;
      if (missing > 0 || untested > 0) {
        try {
          const filled = await runGapFillTests(created.session_id);
          latest = filled;
          setSession(filled);
          const reexecuted = await runExecuteTests(created.session_id);
          latest = reexecuted;
          setSession(reexecuted);
          covered = await runCoverage(created.session_id);
          latest = covered;
          setSession(covered);
        } catch (gapErr) {
          console.warn('Coverage gap-fill notice:', gapErr);
        }
      }
      persistSessionId((covered || latest || created).session_id);
      setStageIndex(9);
      setPhase('complete');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed.');
      if (latest) {
        setSession(latest);
        setPhase('complete');
      } else {
        setPhase('idle');
      }
    } finally {
      runningRef.current = false;
    }
  };

  const reset = () => {
    setPhase('idle');
    setStageIndex(0);
    setError(null);
    setSession(null);
    setDiagramPreview(null);
  };

  const functions: FunctionAnalysis[] = session?.code_analysis?.functions || [];
  const structuredReqs: StructuredRequirement[] =
    session?.requirement_analysis?.requirements || [];
  const whiteBoxTests = session?.white_box_tests?.test_count || 0;
  const blackBoxTests = session?.black_box_tests?.test_count || 0;
  const grayBoxTests = session?.gray_box_tests?.test_count || 0;
  const failedTests = (session?.test_execution?.tests || []).filter(
    (t) => t.status === 'failed' || t.status === 'error'
  );
  const reqCoverage = session?.requirement_coverage;
  const missedLines = (session?.coverage?.source_lines || []).filter((line) => line.status === 'missed');

  return (
    <>
      <section className="relative min-h-screen pt-20 px-4 sm:px-6 lg:px-10 pb-12">
        <div className="max-w-7xl mx-auto mb-6">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-foreground">
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
                    : 'bg-muted-foreground'
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

        <GitHubPicker
          disabled={phase === 'running'}
          onImported={({
            filename: name,
            source_code,
            requirements_text,
            requirements_filename,
          }) => {
            setFilename(name);
            setSourceCode(source_code);
            if (requirements_text.trim()) {
              setRequirements(requirements_text);
              setRequirementsFilename(requirements_filename || 'requirements.txt');
            }
            setError(null);
          }}
          onProjectStart={() => {
            setError(null);
            setSession(null);
            setPhase('running');
            setStageIndex(0);
          }}
          onProjectFailed={(message) => {
            setError(message);
            setPhase('idle');
          }}
          onProjectTested={(payload) => {
            persistSessionId(payload.session_id);
            setSession(payload);
            setFilename(payload.inputs?.original_filename || `${payload.github_agent?.full_name || 'project'}_combined.py`);
            if (payload.source_code) setSourceCode(payload.source_code);
            if (payload.requirements_text) setRequirements(payload.requirements_text);
            setStageIndex(analysisStages.length);
            setPhase('complete');
          }}
        />

        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="rounded-2xl border border-border bg-card overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted">
              <Code2 className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-muted-foreground tracking-wider">SOURCE CODE</span>
              <span className="ml-auto text-xs text-muted-foreground font-mono">{filename}</span>
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
              aria-label="Python source code"
              value={sourceCode}
              onChange={(e) => setSourceCode(e.target.value)}
              disabled={phase === 'running'}
              spellCheck={false}
              className="w-full h-[400px] p-4 bg-transparent font-mono text-xs text-foreground leading-relaxed resize-none outline-none scrollbar-hide"
            />
          </div>

          <div className="rounded-2xl border border-border bg-card overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted flex-wrap">
              <FileText className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-muted-foreground tracking-wider">REQUIREMENTS</span>
              <span className="ml-auto text-xs text-muted-foreground font-mono truncate max-w-[9rem]">
                {requirementsFilename}
              </span>
              <select
                aria-label="Requirements input type"
                value={requirementsInputType}
                onChange={(e) => {
                  const value = e.target.value;
                  if (
                    value === 'text' ||
                    value === 'pdf' ||
                    value === 'document' ||
                    value === 'diagram'
                  ) {
                    setRequirementsInputType(value);
                  }
                }}
                disabled={phase === 'running' || extractingRequirements || extractingDiagram}
                className="rounded border border-border bg-card px-2 py-1 text-xs text-foreground outline-none focus:border-yellow-500 disabled:opacity-50"
              >
                <option value="text">Type or paste text</option>
                <option value="pdf">Upload PDF requirements</option>
                <option value="document">Upload Word/text requirements</option>
                <option value="diagram">Upload flowchart image</option>
              </select>
              {requirementsInputType !== 'text' && (
                <button
                  type="button"
                  onClick={() =>
                    requirementsInputType === 'diagram'
                      ? diagramFileRef.current?.click()
                      : requirementsFileRef.current?.click()
                  }
                  disabled={
                    phase === 'running' ||
                    extractingRequirements ||
                    extractingDiagram
                  }
                  className="flex items-center gap-1 text-xs font-mono text-yellow-500 hover:text-yellow-400 disabled:opacity-50"
                >
                  {requirementsInputType === 'diagram' && <ImageIcon className="w-3 h-3" />}
                  {extractingRequirements
                    ? 'Reading…'
                    : extractingDiagram
                      ? 'Analyzing…'
                      : requirementsInputType === 'pdf'
                        ? 'Choose PDF'
                        : requirementsInputType === 'document'
                          ? 'Choose Document'
                          : 'Choose Image'}
                </button>
              )}
              <input
                ref={requirementsFileRef}
                type="file"
                aria-label="Requirements upload file"
                accept={
                  requirementsInputType === 'pdf'
                    ? '.pdf,application/pdf'
                    : '.doc,.docx,.txt,.md,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown'
                }
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (
                    file &&
                    (requirementsInputType === 'pdf' || requirementsInputType === 'document')
                  ) {
                    onRequirementsUpload(file, requirementsInputType);
                  }
                  e.target.value = '';
                }}
              />
              <input
                ref={diagramFileRef}
                type="file"
                aria-label="Flowchart image file"
                accept=".png,.jpg,.jpeg,.gif,.webp,image/png,image/jpeg,image/gif,image/webp"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) onDiagramUpload(file);
                  e.target.value = '';
                }}
              />
            </div>
            <textarea
              aria-label="Requirements text"
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              disabled={phase === 'running' || extractingRequirements || extractingDiagram}
              spellCheck={false}
              className="w-full h-[400px] p-4 bg-transparent font-mono text-xs text-foreground leading-relaxed resize-none outline-none scrollbar-hide"
            />
            {diagramPreview && (
              <div className="border-t border-border p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs text-muted-foreground">
                    DIAGRAM PREVIEW · {requirementsFilename}
                  </span>
                  {extractingDiagram && (
                    <span className="text-xs text-yellow-500 animate-pulse">Extracting requirements…</span>
                  )}
                  <button
                    type="button"
                    onClick={() => setDiagramPreview(null)}
                    className="text-xs text-muted-foreground hover:text-red-400"
                  >
                    ✕ Remove
                  </button>
                </div>
                <img
                  src={diagramPreview}
                  alt="Uploaded diagram"
                  className="max-h-48 w-full object-contain rounded-lg border border-border"
                />
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-border bg-card overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-border bg-muted">
              <Cpu className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-muted-foreground tracking-wider">AI ENGINE</span>
            </div>
            <div className="relative h-[400px]">
              {show3D && (
                <div className="absolute inset-0">
                  <TestingLabScene scrollProgress={phase === 'running' ? 0.5 : 0} />
                </div>
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent" />
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
                  <div className="h-1 bg-muted rounded-full overflow-hidden">
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
            <LabButton size="lg" onClick={runAnalysis} disabled={backendUp === false} data-testid="run-analysis">
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

        {session?.github_agent && (
          <div className="max-w-7xl mx-auto mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-foreground">GitHub project agent</h3>
              <span className="text-sm text-muted-foreground">
                {session.github_agent.full_name} · {session.github_agent.python_files_tested?.length || 0} modules
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {(session.github_agent.included_modules || []).map((mod) => (
                <div
                  key={mod.path}
                  className="p-4 rounded-xl border border-yellow-500/20 bg-yellow-500/5"
                >
                  <p className="font-mono text-xs text-yellow-500 mb-2">{mod.path}</p>
                  <p className="text-sm text-foreground">{mod.functions.length} functions tested</p>
                </div>
              ))}
            </div>
            {(session.github_agent.skipped_modules?.length || 0) > 0 && (
              <p className="mt-3 text-xs text-muted-foreground">
                Skipped {session.github_agent.skipped_modules?.length} paths (tests, syntax errors, or no top-level functions).
              </p>
            )}
          </div>
        )}

        {functions.length > 0 && (
          <div className="max-w-7xl mx-auto mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-foreground">Source Code Analysis</h3>
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
                    <p className="text-sm text-foreground mb-2">
                      {fn.params.map((p) => p.name).join(', ') || 'no params'}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
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
              <h3 className="text-lg font-bold text-foreground">Requirement Analysis</h3>
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
                    <p className="text-sm text-foreground mb-2">{req.condition}</p>
                    <p className="text-xs text-muted-foreground">{req.expected_result}</p>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        )}
        {blackBoxTests > 0 && (
          <div className="max-w-7xl mx-auto mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-foreground">Black-Box Tests (Task 6)</h3>
              <span className="flex items-center gap-1.5 text-green-500 text-sm">
                <CheckCircle2 className="w-4 h-4" />
                {blackBoxTests} requirement-driven cases
                {session?.black_box_tests?.generation_source
                  ? ` · ${session.black_box_tests.generation_source}`
                  : ''}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {(session?.black_box_tests?.requirements || []).map((req) => (
                <motion.div
                  key={req.requirement_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 rounded-xl border border-blue-500/20 bg-blue-500/5"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs text-yellow-500">{req.requirement_id}</span>
                    <span className="text-xs text-muted-foreground">{req.case_count} cases</span>
                  </div>
                  <ul className="text-sm text-foreground space-y-1">
                    {(req.cases || []).slice(0, 3).map((c) => (
                      <li key={c.case_id} className="truncate">{c.description}</li>
                    ))}
                  </ul>
                </motion.div>
              ))}
            </div>
          </div>
        )}
        {grayBoxTests > 0 && (
          <div className="max-w-7xl mx-auto mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-foreground">Gray-Box Tests (Task 7)</h3>
              <span className="flex items-center gap-1.5 text-green-500 text-sm">
                <CheckCircle2 className="w-4 h-4" />
                {grayBoxTests} requirement + branch cases
                {session?.gray_box_tests?.generation_source
                  ? ` · ${session.gray_box_tests.generation_source}`
                  : ''}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {(session?.gray_box_tests?.test_cases || []).slice(0, 12).map((test) => (
                <motion.div
                  key={test.case_id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 rounded-xl border border-purple-500/20 bg-purple-500/5"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs text-yellow-500">{test.requirement_id}</span>
                    <span className="text-xs text-muted-foreground">{test.function_name}</span>
                  </div>
                  <p className="text-sm text-foreground truncate">{test.description}</p>
                  {test.target_branch && (
                    <p className="mt-2 text-xs text-muted-foreground truncate">{test.target_branch}</p>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        )}
        {whiteBoxTests > 0 && (
          <div className="max-w-7xl mx-auto mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-foreground">White-Box Tests (Task 5)</h3>
              <span className="flex items-center gap-1.5 text-green-500 text-sm">
                <CheckCircle2 className="w-4 h-4" />
                {whiteBoxTests} generated cases
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {(session?.white_box_tests?.functions || [])
                .filter((fn) => fn.status === 'generated')
                .map((fn) => (
                  <motion.div
                    key={fn.function}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-4 rounded-xl border border-border bg-muted"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs text-yellow-500">{fn.function}</span>
                      <span className="text-xs text-muted-foreground">{fn.source}</span>
                    </div>
                    <p className="text-sm text-foreground">{fn.case_count} pytest cases</p>
                  </motion.div>
                ))}
            </div>
          </div>
        )}

        {failedTests.length > 0 && (
          <div className="max-w-7xl mx-auto mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-foreground">Failed tests — fix your code</h3>
              <span className="flex items-center gap-1.5 text-red-400 text-sm">
                <XCircle className="w-4 h-4" />
                {failedTests.length} failed
              </span>
            </div>
            <div className="space-y-3">
              {failedTests.map((test) => (
                <div
                  key={test.test_id}
                  className="p-4 rounded-xl border border-red-500/30 bg-red-500/5"
                >
                  <p className="font-mono text-xs text-red-400 mb-1">{test.test_id}</p>
                  {test.requirement_id && (
                    <p className="text-xs text-yellow-500 mb-2">
                      {test.requirement_id}
                      {test.requirement_condition ? ` — ${test.requirement_condition}` : ''}
                    </p>
                  )}
                  <p className="text-sm text-foreground mb-2">{test.why_failed || 'This test failed.'}</p>
                  {test.expected_value && (
                    <p className="text-xs text-muted-foreground mb-1">
                      Expected {test.expected_value}
                      {test.actual_value ? ` · got ${test.actual_value}` : ''}
                    </p>
                  )}
                  <p className="text-sm text-foreground">{test.how_to_fix}</p>
                  {test.error_message && (
                    <pre className="mt-2 text-[11px] text-muted-foreground whitespace-pre-wrap max-h-40 overflow-auto">
                      {test.error_message}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {reqCoverage && (reqCoverage.requirements?.length || 0) > 0 && (
          <div className="max-w-7xl mx-auto mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-foreground">Requirement coverage</h3>
              <span className="text-sm text-muted-foreground">
                {reqCoverage.tested_count}/{reqCoverage.requirement_count} requirements tested
                {reqCoverage.coverage_percent != null ? ` · ${reqCoverage.coverage_percent}%` : ''}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {(reqCoverage.requirements || []).map((row) => (
                <div
                  key={row.requirement_id}
                  className={`p-4 rounded-xl border ${
                    row.status === 'passed'
                      ? 'border-green-500/20 bg-green-500/5'
                      : row.status === 'failed'
                      ? 'border-red-500/30 bg-red-500/5'
                      : 'border-border bg-muted'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-mono text-xs text-yellow-500">{row.requirement_id}</span>
                    <span className="text-xs text-muted-foreground">{row.status}</span>
                  </div>
                  <p className="text-sm text-foreground">{row.condition}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {(session?.coverage?.source_lines?.length || 0) > 0 && (
          <div className="max-w-7xl mx-auto mt-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-foreground">Source line coverage</h3>
              <span className="text-sm text-muted-foreground">
                {session?.coverage?.overall_line_coverage_percent != null
                  ? `${session.coverage.overall_line_coverage_percent}% lines`
                  : ''}
                {missedLines.length ? ` · ${missedLines.length} missed` : ' · all measured lines hit'}
              </span>
            </div>
            <pre className="p-4 rounded-xl border border-border bg-card text-card-foreground overflow-auto max-h-96 font-mono text-xs leading-5">
              {(session?.coverage?.source_lines || []).map((line) => (
                <div
                  key={line.lineno}
                  className={
                    line.status === 'missed'
                      ? 'text-red-400 bg-red-500/10'
                      : line.status === 'covered'
                      ? 'text-green-500/80'
                      : 'text-muted-foreground'
                  }
                >
                  <span className="inline-block w-10 text-muted-foreground">{line.lineno}</span>
                  {line.status === 'missed' ? '✗ ' : '  '}
                  {line.text}
                </div>
              ))}
            </pre>
          </div>
        )}
      </section>

      <Footer />
    </>
  );
}
