'use client';

import { useState, useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import { motion } from 'motion/react';
import { Footer } from '@/components/navigation/Footer';
import { SectionHeading } from '@/components/ui/SectionHeading';
import {
  CheckCircle2,
  XCircle,
  Clock,
  Target,
  Activity,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
} from 'recharts';

const CoverageSphereCanvas = dynamic(
  () => import('@/components/3d/CoverageSphereCanvas').then((m) => m.CoverageSphereCanvas),
  { ssr: false, loading: () => <div className="flex items-center justify-center h-full"><div className="w-8 h-8 border-2 border-yellow-500/30 border-t-yellow-500 rounded-full animate-spin" /></div> }
);

const mockResults = [
  { reqId: 'REQ-01', testCase: 'TC-001', type: 'Unit', module: 'Auth', status: 'passed', severity: '-', coverage: 98 },
  { reqId: 'REQ-02', testCase: 'TC-002', type: 'Negative', module: 'Auth', status: 'passed', severity: '-', coverage: 95 },
  { reqId: 'REQ-03', testCase: 'TC-003', type: 'Integration', module: 'Session', status: 'failed', severity: 'HIGH', coverage: 72 },
  { reqId: 'REQ-04', testCase: 'TC-006', type: 'Regression', module: 'Auth', status: 'failed', severity: 'MEDIUM', coverage: 81 },
  { reqId: 'REQ-05', testCase: 'TC-007', type: 'Integration', module: 'API', status: 'passed', severity: '-', coverage: 94 },
  { reqId: 'REQ-06', testCase: 'TC-008', type: 'Unit', module: 'Upload', status: 'passed', severity: '-', coverage: 99 },
  { reqId: 'REQ-07', testCase: 'TC-009', type: 'White Box', module: 'Auth', status: 'passed', severity: '-', coverage: 92 },
  { reqId: 'REQ-08', testCase: 'TC-010', type: 'Negative', module: 'Network', status: 'failed', severity: 'HIGH', coverage: 68 },
  { reqId: 'REQ-01', testCase: 'TC-011', type: 'Regression', module: 'Cache', status: 'passed', severity: '-', coverage: 96 },
  { reqId: 'REQ-05', testCase: 'TC-012', type: 'Black Box', module: 'Data', status: 'passed', severity: '-', coverage: 91 },
];

const coverageData = [
  { name: 'Statements', value: 95.4, fill: '#FACC15' },
  { name: 'Branches', value: 87.2, fill: '#FFD60A' },
  { name: 'Functions', value: 92.1, fill: '#A16207' },
  { name: 'Lines', value: 96.8, fill: '#FACC15' },
];

const executionData = [
  { module: 'Auth', passed: 12, failed: 2 },
  { module: 'Session', passed: 8, failed: 1 },
  { module: 'API', passed: 15, failed: 0 },
  { module: 'Upload', passed: 6, failed: 0 },
  { module: 'Network', passed: 4, failed: 2 },
  { module: 'Cache', passed: 9, failed: 1 },
];

const timelineTests = Array.from({ length: 40 }).map((_, i) => ({
  id: i,
  status: i % 5 === 0 ? 'failed' : i % 3 === 0 ? 'running' : 'passed',
  delay: i * 0.5,
}));

export default function DashboardPage() {
  const [filter, setFilter] = useState<'all' | 'passed' | 'failed'>('all');
  const [sortKey, setSortKey] = useState<'reqId' | 'coverage' | 'severity'>('reqId');
  const [timelineProgress, setTimelineProgress] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return;
    const interval = setInterval(() => {
      setTimelineProgress((p) => (p >= 100 ? 0 : p + 0.5));
    }, 30);
    return () => clearInterval(interval);
  }, [paused]);

  const filteredResults = mockResults
    .filter((r) => filter === 'all' || r.status === filter)
    .sort((a, b) => {
      if (sortKey === 'coverage') return b.coverage - a.coverage;
      if (sortKey === 'severity') {
        const order = { HIGH: 0, MEDIUM: 1, '-': 2 };
        return order[a.severity as keyof typeof order] - order[b.severity as keyof typeof order];
      }
      return a.reqId.localeCompare(b.reqId);
    });

  return (
    <>
      <section className="relative pt-24 px-6 sm:px-10 lg:px-20 pb-12">
        {/* Header */}
        <div className="max-w-7xl mx-auto mb-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className="font-mono text-xs text-yellow-500 tracking-wider">AI TESTING COMMAND CENTER</span>
                <span className="px-2 py-0.5 rounded-full bg-green-500/10 text-green-500 text-xs font-mono">COMPLETED</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-bold text-white">
                Test Run <span className="font-mono text-yellow-500">#RUN-2847</span>
              </h1>
            </div>
            <div className="text-sm text-neutral-500 font-mono">
              {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
            </div>
          </div>
        </div>

        {/* Metrics row */}
        <div className="max-w-7xl mx-auto grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[
            { label: 'TEST CASES', value: '1,284', icon: Activity, color: 'text-yellow-500' },
            { label: 'PASSED', value: '1,194', icon: CheckCircle2, color: 'text-green-500' },
            { label: 'FAILED', value: '90', icon: XCircle, color: 'text-red-500' },
            { label: 'COVERAGE', value: '95.4%', icon: Target, color: 'text-yellow-500' },
          ].map((metric, i) => (
            <motion.div
              key={i}
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

        {/* 3D Coverage + Coverage chart */}
        <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
          <div className="rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800">
              <Target className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">3D COVERAGE SPHERE</span>
            </div>
            <div className="h-[400px] relative">
              <CoverageSphereCanvas coverage={0.954} />
              <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between">
                <div className="flex items-center gap-4 text-xs">
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-yellow-500" />
                    <span className="text-neutral-400">Covered</span>
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-neutral-700" />
                    <span className="text-neutral-400">Uncovered</span>
                  </span>
                </div>
                <span className="font-mono text-2xl font-bold text-yellow-500">95.4%</span>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800">
              <Activity className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">COVERAGE BREAKDOWN</span>
            </div>
            <div className="p-6 h-[400px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart data={coverageData} innerRadius="20%" outerRadius="90%" startAngle={90} endAngle={-270}>
                  <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                  <RadialBar background={{ fill: '#1a1a1a' }} dataKey="value" cornerRadius={8} />
                  <Tooltip
                    contentStyle={{ background: '#0a0a0a', border: '1px solid #262626', borderRadius: '8px', color: '#fff' }}
                  />
                </RadialBarChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-2 mt-4">
                {coverageData.map((item, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="w-2 h-2 rounded-full" style={{ background: item.fill }} />
                    <span className="text-neutral-400">{item.name}</span>
                    <span className="ml-auto text-white font-mono">{item.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Execution timeline */}
        <div className="max-w-7xl mx-auto rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden mb-8">
          <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-800">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-yellow-500" />
              <span className="font-mono text-xs text-neutral-400 tracking-wider">EXECUTION TIMELINE</span>
            </div>
            <button
              onClick={() => setPaused(!paused)}
              className="px-3 py-1 rounded-lg border border-neutral-700 text-xs text-neutral-400 hover:text-yellow-500 hover:border-yellow-500/50 transition-colors"
            >
              {paused ? '▶ Resume' : '⏸ Pause'}
            </button>
          </div>
          <div className="p-6">
            {/* Timeline track */}
            <div className="relative h-16 mb-4">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full h-px bg-neutral-800" />
              </div>
              {/* Progress line */}
              <div
                className="absolute top-1/2 -translate-y-1/2 h-px bg-yellow-500"
                style={{ width: `${timelineProgress}%`, boxShadow: '0 0 8px rgba(250,204,21,0.5)' }}
              />
              {/* Test nodes */}
              {timelineTests.map((test, i) => {
                const pos = (i / timelineTests.length) * 100;
                const visible = timelineProgress >= pos;
                return (
                  <div
                    key={i}
                    className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 transition-all"
                    style={{ left: `${pos}%` }}
                  >
                    <motion.div
                      animate={{ scale: visible ? 1 : 0 }}
                      className={`w-3 h-3 rounded-full border ${
                        test.status === 'failed' ? 'bg-red-500 border-red-500' :
                        test.status === 'running' ? 'bg-yellow-500 border-yellow-500 animate-pulse' :
                        'bg-green-500 border-green-500'
                      }`}
                    />
                  </div>
                );
              })}
            </div>
            {/* Status labels */}
            <div className="flex items-center justify-between text-xs font-mono text-neutral-500">
              <span>QUEUED</span>
              <span>RUNNING</span>
              <span className="text-green-500">PASSED</span>
              <span className="text-red-500">FAILED</span>
            </div>
          </div>
        </div>

        {/* Execution chart */}
        <div className="max-w-7xl mx-auto rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden mb-8">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800">
            <Activity className="w-4 h-4 text-yellow-500" />
            <span className="font-mono text-xs text-neutral-400 tracking-wider">RESULTS BY MODULE</span>
          </div>
          <div className="p-6 h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={executionData}>
                <XAxis dataKey="module" stroke="#525252" fontSize={12} />
                <YAxis stroke="#525252" fontSize={12} />
                <Tooltip
                  contentStyle={{ background: '#0a0a0a', border: '1px solid #262626', borderRadius: '8px', color: '#fff' }}
                  cursor={{ fill: 'rgba(250,204,21,0.05)' }}
                />
                <Bar dataKey="passed" fill="#22C55E" radius={[4, 4, 0, 0]} />
                <Bar dataKey="failed" fill="#EF4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Traceability graph (simplified) */}
        <div className="max-w-7xl mx-auto rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden mb-8">
          <div className="flex items-center gap-2 px-4 py-3 border-b border-neutral-800">
            <span className="font-mono text-xs text-neutral-400 tracking-wider">TRACEABILITY GRAPH</span>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {['REQ-01', 'REQ-03', 'REQ-05', 'REQ-08'].map((req) => {
                const tests = mockResults.filter((r) => r.reqId === req);
                const hasFailed = tests.some((t) => t.status === 'failed');
                return (
                  <div key={req} className="flex items-center gap-4">
                    <div className={`px-3 py-2 rounded-lg border font-mono text-xs ${
                      hasFailed ? 'border-red-500/30 bg-red-500/5 text-red-500' :
                      'border-yellow-500/30 bg-yellow-500/5 text-yellow-500'
                    }`}>
                      {req}
                    </div>
                    <div className="flex-1 h-px bg-neutral-800" />
                    <div className="flex gap-2">
                      {tests.map((t) => (
                        <div
                          key={t.testCase}
                          className={`px-2 py-1 rounded text-xs font-mono ${
                            t.status === 'failed' ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'
                          }`}
                        >
                          {t.testCase}
                        </div>
                      ))}
                    </div>
                    <div className="flex-1 h-px bg-neutral-800" />
                    <div className="text-xs text-neutral-500">
                      {tests[0]?.module}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Results table */}
        <div className="max-w-7xl mx-auto rounded-2xl border border-neutral-800 bg-neutral-950 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-800">
            <span className="font-mono text-xs text-neutral-400 tracking-wider">RESULTS TABLE</span>
            <div className="flex items-center gap-2">
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value as 'all' | 'passed' | 'failed')}
                className="bg-neutral-900 border border-neutral-700 text-xs text-neutral-300 rounded-lg px-2 py-1"
              >
                <option value="all">All</option>
                <option value="passed">Passed</option>
                <option value="failed">Failed</option>
              </select>
              <select
                value={sortKey}
                onChange={(e) => setSortKey(e.target.value as 'reqId' | 'coverage' | 'severity')}
                className="bg-neutral-900 border border-neutral-700 text-xs text-neutral-300 rounded-lg px-2 py-1"
              >
                <option value="reqId">Sort: Requirement</option>
                <option value="coverage">Sort: Coverage</option>
                <option value="severity">Sort: Severity</option>
              </select>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-800">
                  {['Req ID', 'Test Case', 'Type', 'Module', 'Status', 'Severity', 'Coverage'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-mono text-neutral-500 uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredResults.map((r, i) => (
                  <tr
                    key={i}
                    className="border-b border-neutral-900 hover:bg-neutral-900/30 transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-yellow-500">{r.reqId}</td>
                    <td className="px-4 py-3 font-mono text-xs text-white">{r.testCase}</td>
                    <td className="px-4 py-3 text-xs text-neutral-400">{r.type}</td>
                    <td className="px-4 py-3 text-xs text-neutral-400">{r.module}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        r.status === 'passed' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'
                      }`}>
                        {r.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {r.severity !== '-' && (
                        <span className={`text-xs font-mono ${
                          r.severity === 'HIGH' ? 'text-red-500' : 'text-yellow-500'
                        }`}>
                          {r.severity}
                        </span>
                      )}
                      {r.severity === '-' && <span className="text-neutral-600">—</span>}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1 bg-neutral-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${r.coverage > 90 ? 'bg-green-500' : r.coverage > 75 ? 'bg-yellow-500' : 'bg-red-500'}`}
                            style={{ width: `${r.coverage}%` }}
                          />
                        </div>
                        <span className="text-xs text-neutral-400 font-mono">{r.coverage}%</span>
                      </div>
                    </td>
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
