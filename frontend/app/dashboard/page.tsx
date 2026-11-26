'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'motion/react';
import { Footer } from '@/components/navigation/Footer';
import {
  CheckCircle2,
  Clock,
  Target,
  Activity,
  Code2,
  FileText,
  FileDown,
  XCircle,
  ExternalLink,
  Layers,
  Filter,
} from 'lucide-react';
import {
  downloadSessionReport,
  getSession,
  readStoredSessionId,
  type FunctionAnalysis,
  type SessionPayload,
  type StructuredRequirement,
} from '@/lib/api';

const CoverageSphereCanvas = dynamic(
  () => import('@/components/3d/CoverageSphereCanvas').then((m) => m.CoverageSphereCanvas),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full">
        <div className="w-8 h-8 border-2 border-yellow-500/30 border-t-yellow-500 rounded-full animate-spin" />
      </div>
    ),
  }
);

function summarize(session: SessionPayload | null) {
  const functions = session?.code_analysis?.functions || [];
  const reqs = session?.requirement_analysis?.requirements || [];
  const branches = functions.reduce((sum, fn) => sum + (fn.branch_count || 0), 0);
  const complexity =
    functions.length === 0
      ? 0
      : Math.round(
          (functions.reduce((sum, fn) => sum + fn.cyclomatic_complexity, 0) / functions.length) * 10
        ) / 10;
  const execution = session?.test_execution;
  const coveragePct = session?.coverage?.overall_line_coverage_percent;
  const completeness = Math.min(
    1,
    (functions.length ? 0.2 : 0) +
    (reqs.length ? 0.2 : 0) +
    ((session?.white_box_tests?.test_count || 0) > 0 ? 0.15 : 0) +
    ((session?.black_box_tests?.test_count || 0) > 0 ? 0.15 : 0) +
    ((session?.gray_box_tests?.test_count || 0) > 0 ? 0.1 : 0) +
    ((session?.other_tests?.negative_count || 0) + (session?.other_tests?.integration_count || 0) > 0 ? 0.1 : 0) +
    (execution?.total ? 0.1 : 0) +
    (coveragePct != null ? 0.1 : 0)
  );
  return { functions, reqs, branches, complexity, completeness, execution, coveragePct };
}

function getTestCategory(testId: string = ''): string {
  const tid = testId.toLowerCase();
  if (tid.includes('white_box')) return 'White-Box';
  if (tid.includes('black_box')) return 'Black-Box';
  if (tid.includes('integration')) return 'Integration';
  if (tid.includes('negative')) return 'Negative';
  if (tid.includes('gap')) return 'Gap-Fill';
  return 'Unit Test';
}

function cleanTestName(testId: string = ''): string {
  const tid = testId.toLowerCase();
  const caseMatch = testId.match(/case_?(\d+)/i);
  const caseNum = caseMatch ? `Case ${caseMatch[1]}` : 'Test';
  const reqMatch = testId.match(/\[(REQ[-_]\d+)\]/i) || testId.match(/_(REQ[-_]\d+)/i);
  const reqTag = reqMatch ? ` (${reqMatch[1].replace('_', '-').toUpperCase()})` : '';

  if (tid.includes('black_box')) return `Black-Box ${caseNum}${reqTag}`;
  if (tid.includes('gray_box')) return `Gray-Box ${caseNum}${reqTag}`;
  if (tid.includes('white_box')) return `White-Box Branch ${caseMatch ? caseMatch[1] : '1'}`;
  if (tid.includes('integration')) return `Integration Scenario ${caseMatch ? caseMatch[1] : '1'}`;
  if (tid.includes('negative')) return `Negative Boundary ${caseMatch ? caseMatch[1] : '1'}`;
  if (tid.includes('gap')) return `Gap-Fill Case ${caseMatch ? caseMatch[1] : '1'}`;

  const parts = testId.split('::');
  return (parts[parts.length - 1] || testId).replace(/\[.*?\]/, '').replace(/_/g, ' ');
}

export default function DashboardPage() {
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reportError, setReportError] = useState<string | null>(null);
  const [downloadingReport, setDownloadingReport] = useState(false);
  const [viewingReport, setViewingReport] = useState(false);
  const [testFilter, setTestFilter] = useState<'all' | 'passed' | 'failed' | 'skipped'>('all');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('session') || readStoredSessionId();
    if (!id) {
      setLoading(false);
      return;
    }
    getSession(id)
      .then(setSession)
      .catch((err) => setError(err instanceof Error ? err.message : 'Could not load session.'))
      .finally(() => setLoading(false));
  }, []);

  const { functions, reqs, branches, complexity, completeness, execution, coveragePct } =
    summarize(session);

  const allTests = execution?.tests || [];
  const passedTests = allTests.filter((t) => t.status === 'passed');
  const failedTests = allTests.filter((t) => t.status === 'failed' || t.status === 'error');
  const skippedTests = allTests.filter((t) => t.status === 'skipped');

  const displayedTests =
    testFilter === 'all'
      ? allTests
      : testFilter === 'passed'
      ? passedTests
      : testFilter === 'failed'
      ? failedTests
      : skippedTests;

  const reqCoverage = session?.requirement_coverage;
  const sourceLines = session?.coverage?.source_lines || [];

  return (
    <>
      <section className="relative pt-24 px-6 sm:px-10 lg:px-20 pb-12">
        <div className="max-w-7xl mx-auto mb-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className="font-mono text-xs text-yellow-500 tracking-wider">
                  AI TESTING COMMAND CENTER
                </span>
                <span className="px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-500 text-xs font-mono">
                  FULL PIPELINE
                </span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white">
                Analysis{' '}
                <span className="font-mono text-yellow-500">
                  {session ? `#${session.session_id}` : '—'}
                </span>
              </h1>
            </div>
            <div className="flex flex-col items-start sm:items-end gap-2">
              <div className="text-sm text-neutral-500 font-mono">
                {session?.status || (loading ? 'LOADING' : 'NO SESSION')}
              </div>
              {session && (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={viewingReport}
                    onClick={async () => {
                      setViewingReport(true);
                      setReportError(null);
                      try {
                        const res = await fetch(`/api/sessions/${session.session_id}/report`);
                        if (!res.ok) throw new Error('Could not load report.');
                        const blob = await res.blob();
                        const url = URL.createObjectURL(blob);
                        window.open(url, '_blank');
                      } catch (err) {
                        setReportError(err instanceof Error ? err.message : 'Could not view report.');
                      } finally {
                        setViewingReport(false);
                      }
                    }}
                    className="inline-flex items-center gap-2 border border-yellow-500/60 bg-yellow-500/10 px-3 py-2 text-sm text-yellow-400 hover:bg-yellow-500/20 disabled:cursor-wait disabled:opacity-50"
                  >
                    <ExternalLink className="h-4 w-4" />
                    {viewingReport ? 'Opening report…' : 'View Full Report'}
                  </button>
                  <button
                    type="button"
                    disabled={downloadingReport}
                    onClick={async () => {
                      setDownloadingReport(true);
                      setReportError(null);
                      try {
                        await downloadSessionReport(session.session_id);
                      } catch (err) {
                        setReportError(err instanceof Error ? err.message : 'Could not download report.');
                      } finally {
                        setDownloadingReport(false);
                      }
                    }}
                    className="inline-flex items-center gap-2 border border-neutral-700 px-3 py-2 text-sm text-neutral-200 hover:border-yellow-500 hover:text-yellow-400 disabled:cursor-wait disabled:opacity-50"
                  >
                    <FileDown className="h-4 w-4" />
                    {downloadingReport ? 'Preparing…' : 'Download HTML'}
                  </button>
                </div>
              )}
              {reportError && <p role="alert" className="text-xs text-red-400">{reportError}</p>}
            </div>
          </div>
        </div>

        {!loading && !session && (
          <div className="max-w-7xl mx-auto mb-8 rounded-2xl border border-neutral-800 bg-neutral-950 p-8 text-center">
            <p className="text-neutral-400">
              No analysis session yet. Run analysis from the Live Lab first.
            </p>
            <a href="/live-lab" className="inline-block mt-4 text-yellow-500 font-mono text-sm">
              Open Live Lab →
            </a>
            {error && <p className="mt-3 text-sm text-red-400 font-mono">{error}</p>}
          </div>
        )}

        <div className="max-w-7xl mx-auto grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'TESTS RUN', value: String(execution?.total ?? 0), icon: Activity, color: 'text-yellow-500' },
            { label: 'PASSED', value: String(execution?.passed ?? 0), icon: CheckCircle2, color: 'text-green-500' },
            { label: 'FAILED', value: String(execution?.failed ?? 0), icon: CheckCircle2, color: 'text-red-500' },
            {
              label: 'LINE COVERAGE',
              value: coveragePct != null ? `${coveragePct}%` : '—',
              icon: Target,
              color: 'text-yellow-500',
            },
          ].map((metric, i) => (
            <motion.div
              key={metric.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              className="p-5 rounded-2xl border border-neutral-800 bg-gradient-to-b from-neutral-900/50 to-transparent"
            >
              <div className="flex items-center justify-between mb-3">
                <metric.icon className={`w-5 h-5 ${metric.color}`} />
                <span className="text-xs font-mono text-neutral-600">{metric.label}</span>
              </div>
              <div className="text-3xl font-bold text-white tabular-nums">{metric.value}</div>
            </motion.div>
          ))}
        </div>

        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
          <div className="rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800">
              <Target className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">ANALYSIS COMPLETENESS</span>
            </div>
            <div className="h-[400px] relative">
              <CoverageSphereCanvas coverage={completeness} />
              <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
                <span className="text-xs text-neutral-400">Pipeline completeness</span>
                <span className="font-mono text-2xl font-bold text-yellow-500">
                  {Math.round(completeness * 100)}%
                </span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800">
              <Clock className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">SOURCE PREVIEW</span>
            </div>
            <pre className="p-4 h-[400px] overflow-auto scrollbar-hide font-mono text-xs text-neutral-300 whitespace-pre-wrap">
              {session?.source_code || 'Source appears here after Live Lab analysis.'}
            </pre>
          </div>
        </div>

        <div className="max-w-7xl mx-auto rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden mb-8">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800">
            <Code2 className="w-4 h-4 text-yellow-500" />
            <span className="font-mono text-xs text-neutral-400 tracking-wider">FUNCTIONS</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-800">
                  {['Function', 'Params', 'Lines', 'Branches', 'Complexity'].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-mono text-neutral-500 uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {functions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-neutral-500 text-sm">
                      No functions yet.
                    </td>
                  </tr>
                )}
                {functions.map((fn: FunctionAnalysis) => (
                  <tr key={fn.qualified_name} className="border-b border-neutral-900 hover:bg-neutral-900/30">
                    <td className="px-4 py-3 font-mono text-xs text-yellow-500">{fn.qualified_name}</td>
                    <td className="px-4 py-3 text-xs text-neutral-400">
                      {fn.params.map((p) => p.name).join(', ') || '—'}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-white">
                      {fn.lineno}–{fn.end_lineno}
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-400">{fn.branch_count}</td>
                    <td className="px-4 py-3 text-xs text-white">{fn.cyclomatic_complexity}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="max-w-7xl mx-auto rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800">
            <CheckCircle2 className="w-4 h-4 text-yellow-500" />
            <span className="font-mono text-xs text-neutral-400 tracking-wider">STRUCTURED REQUIREMENTS</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-800">
                  {['Req ID', 'Condition', 'Expected result'].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-mono text-neutral-500 uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {reqs.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-6 text-neutral-500 text-sm">
                      No structured requirements yet. Requirement analysis runs from Live Lab (Task 4).
                    </td>
                  </tr>
                )}
                {reqs.map((req: StructuredRequirement) => (
                  <tr key={req.requirement_id} className="border-b border-neutral-900 hover:bg-neutral-900/30">
                    <td className="px-4 py-3 font-mono text-xs text-yellow-500">{req.requirement_id}</td>
                    <td className="px-4 py-3 text-xs text-white">{req.condition}</td>
                    <td className="px-4 py-3 text-xs text-neutral-400">{req.expected_result}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ALL GENERATED TEST CASES TABLE */}
        <div className="max-w-7xl mx-auto mt-8 rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-4 py-3 border-b border-neutral-800">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">
                COMPLETE GENERATED TEST SUITE
              </span>
              <span className="text-xs font-mono text-neutral-500">
                ({allTests.length} Total)
              </span>
            </div>
            <div className="flex items-center gap-1.5 bg-neutral-900/60 p-1 rounded-lg border border-neutral-800 text-xs font-mono">
              <button
                type="button"
                onClick={() => setTestFilter('all')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  testFilter === 'all'
                    ? 'bg-yellow-500/20 text-yellow-400 font-bold border border-yellow-500/30'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                All ({allTests.length})
              </button>
              <button
                type="button"
                onClick={() => setTestFilter('passed')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  testFilter === 'passed'
                    ? 'bg-green-500/20 text-green-400 font-bold border border-green-500/30'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                Passed ({passedTests.length})
              </button>
              <button
                type="button"
                onClick={() => setTestFilter('failed')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  testFilter === 'failed'
                    ? 'bg-red-500/20 text-red-400 font-bold border border-red-500/30'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                Failed ({failedTests.length})
              </button>
              {skippedTests.length > 0 && (
                <button
                  type="button"
                  onClick={() => setTestFilter('skipped')}
                  className={`px-2.5 py-1 rounded transition-colors ${
                    testFilter === 'skipped'
                      ? 'bg-neutral-700 text-neutral-200 font-bold border border-neutral-600'
                      : 'text-neutral-400 hover:text-white'
                  }`}
                >
                  Skipped ({skippedTests.length})
                </button>
              )}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-800">
                  {['Target Req', 'Category', 'Test Case', 'Expected Result', 'Result Came (Actual)', 'Status'].map((h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-xs font-mono text-neutral-500 uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {displayedTests.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-neutral-500 text-sm">
                      {allTests.length === 0
                        ? 'No test cases generated yet. Run test generation in Live Lab.'
                        : `No test cases matching filter "${testFilter}".`}
                    </td>
                  </tr>
                )}
                {displayedTests.map((test) => {
                  const cat = getTestCategory(test.test_id);
                  const cleanName = cleanTestName(test.test_id);
                  const isPassed = test.status === 'passed';
                  const isFailed = test.status === 'failed' || test.status === 'error';
                  const isSkipped = test.status === 'skipped';

                  return (
                    <tr
                      key={test.test_id}
                      className="border-b border-neutral-900 hover:bg-neutral-900/30"
                    >
                      <td className="px-4 py-3 text-xs">
                        {test.requirement_id ? (
                          <span className="font-mono text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded border border-yellow-500/20 font-bold">
                            {test.requirement_id}
                          </span>
                        ) : (
                          <span className="text-neutral-500 text-[11px] font-mono">GENERAL</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        <span
                          className={`inline-block px-2 py-0.5 rounded text-[11px] font-mono border ${
                            cat === 'White-Box'
                              ? 'border-indigo-500/40 text-indigo-300 bg-indigo-500/10'
                              : cat === 'Black-Box'
                              ? 'border-cyan-500/40 text-cyan-300 bg-cyan-500/10'
                              : cat === 'Gray-Box'
                              ? 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10'
                              : cat === 'Integration'
                              ? 'border-purple-500/40 text-purple-300 bg-purple-500/10'
                              : 'border-orange-500/40 text-orange-300 bg-orange-500/10'
                          }`}
                        >
                          {cat}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-white">
                        <div className="font-semibold text-neutral-200">{cleanName}</div>
                        <div className="text-[10px] text-neutral-500 truncate max-w-xs">
                          {test.test_id.split('::').pop()}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-neutral-300">
                        <span className="font-mono font-medium">
                          {test.expected_value || test.requirement_expected || 'Valid execution'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs max-w-sm">
                        {isPassed && (
                          <span className="text-green-400 font-mono text-[11.5px] font-medium">
                            ✓ {test.expected_value ? `Matches ${test.expected_value}` : 'Passed as expected'}
                          </span>
                        )}
                        {isFailed && (
                          <div>
                            <p className="text-red-400 font-mono text-[11.5px] font-semibold mb-0.5">
                              ✗ {test.actual_value ? `Got ${test.actual_value}` : (test.why_failed || 'Failed assertion')}
                            </p>
                            {test.how_to_fix && (
                              <p className="text-neutral-500 text-[10.5px]">{test.how_to_fix}</p>
                            )}
                          </div>
                        )}
                        {isSkipped && (
                          <span className="text-neutral-400 font-mono text-xs">Skipped</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        {isPassed && (
                          <span className="inline-flex items-center gap-1.5 text-green-400 font-mono font-bold">
                            <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                            PASS
                          </span>
                        )}
                        {isFailed && (
                          <span className="inline-flex items-center gap-1.5 text-red-400 font-mono font-bold">
                            <XCircle className="w-3.5 h-3.5 text-red-500" />
                            FAIL
                          </span>
                        )}
                        {isSkipped && (
                          <span className="inline-flex items-center gap-1.5 text-neutral-400 font-mono">
                            SKIPPED
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {failedTests.length > 0 && (
          <div className="max-w-7xl mx-auto mt-8 rounded-2xl border border-red-500/30 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-red-500/20">
              <XCircle className="w-4 h-4 text-red-400" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">
                FAILED TESTS — WHY THEY FAILED
              </span>
            </div>
            <div className="divide-y divide-neutral-900">
              {failedTests.map((test) => (
                <div key={test.test_id} className="p-4">
                  <p className="font-mono text-xs text-red-400 mb-1">{test.test_id}</p>
                  {test.requirement_id && (
                    <p className="text-xs text-yellow-500 mb-1">
                      {test.requirement_id}
                      {test.requirement_condition ? ` — ${test.requirement_condition}` : ''}
                    </p>
                  )}
                  <p className="text-sm text-white mb-1">{test.why_failed || 'This test failed.'}</p>
                  <p className="text-sm text-neutral-300">{test.how_to_fix}</p>
                  {test.error_message && (
                    <pre className="mt-2 text-[11px] text-neutral-500 whitespace-pre-wrap max-h-32 overflow-auto">
                      {test.error_message}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {reqCoverage && (reqCoverage.requirements?.length || 0) > 0 && (
          <div className="max-w-7xl mx-auto mt-8 rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800">
              <FileText className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">
                REQUIREMENT FILE COVERAGE
              </span>
              <span className="ml-auto text-xs text-neutral-500">
                {reqCoverage.tested_count}/{reqCoverage.requirement_count}
                {reqCoverage.coverage_percent != null ? ` · ${reqCoverage.coverage_percent}%` : ''}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-800">
                    {['Req ID', 'Condition', 'Status', 'Tests'].map((h) => (
                      <th
                        key={h}
                        className="px-4 py-3 text-left text-xs font-mono text-neutral-500 uppercase tracking-wider"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(reqCoverage.requirements || []).map((row) => (
                    <tr key={row.requirement_id} className="border-b border-neutral-900">
                      <td className="px-4 py-3 font-mono text-xs text-yellow-500">{row.requirement_id}</td>
                      <td className="px-4 py-3 text-xs text-white">{row.condition}</td>
                      <td className={`px-4 py-3 text-xs ${
                        row.status === 'passed'
                          ? 'text-green-500'
                          : row.status === 'failed'
                          ? 'text-red-400'
                          : 'text-neutral-500'
                      }`}>
                        {row.status}
                      </td>
                      <td className="px-4 py-3 text-xs">
                        <div className="font-mono text-neutral-300 font-semibold mb-1">
                          {row.test_count} test{row.test_count === 1 ? '' : 's'}
                        </div>
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {allTests
                            .filter((t) => t.requirement_id === row.requirement_id)
                            .map((t) => {
                              const isP = t.status === 'passed';
                              const isF = t.status === 'failed' || t.status === 'error';
                              return (
                                <span
                                  key={t.test_id}
                                  title={t.test_id}
                                  className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-mono border ${
                                    isP
                                      ? 'border-green-500/30 text-green-400 bg-green-500/10'
                                      : isF
                                      ? 'border-red-500/30 text-red-400 bg-red-500/10'
                                      : 'border-neutral-700 text-neutral-400 bg-neutral-900'
                                  }`}
                                >
                                  {cleanTestName(t.test_id)}
                                </span>
                              );
                            })}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {sourceLines.length > 0 && (
          <div className="max-w-7xl mx-auto mt-8 rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800">
              <Target className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">SOURCE LINE COVERAGE</span>
              <span className="ml-auto text-xs text-neutral-500">
                {coveragePct != null ? `${coveragePct}%` : ''}
              </span>
            </div>
            <pre className="p-4 max-h-96 overflow-auto font-mono text-xs leading-5">
              {sourceLines.map((line) => (
                <div
                  key={line.lineno}
                  className={
                    line.status === 'missed'
                      ? 'text-red-400 bg-red-500/10'
                      : line.status === 'covered'
                      ? 'text-green-500/80'
                      : 'text-neutral-600'
                  }
                >
                  <span className="inline-block w-10 text-neutral-600">{line.lineno}</span>
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
