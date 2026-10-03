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
  const completeness =
    (functions.length ? 0.25 : 0) +
    (reqs.length ? 0.25 : 0) +
    ((session?.white_box_tests?.test_count || 0) > 0 ? 0.25 : 0) +
    (execution?.total ? 0.25 : 0);
  return { functions, reqs, branches, complexity, completeness, execution, coveragePct };
}

export default function DashboardPage() {
  const [session, setSession] = useState<SessionPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reportError, setReportError] = useState<string | null>(null);
  const [downloadingReport, setDownloadingReport] = useState(false);

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
                  {downloadingReport ? 'Preparing report…' : 'Download report'}
                </button>
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
                      No structured requirements yet. Gemini analysis runs from Live Lab (Task 4).
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
      </section>

      <Footer />
    </>
  );
}
