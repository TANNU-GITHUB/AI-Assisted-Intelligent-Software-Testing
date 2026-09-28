export const SESSION_STORAGE_KEY = 'bugai_session_id';

export type FunctionAnalysis = {
  name: string;
  qualified_name: string;
  params: { name: string; annotation: string | null }[];
  return_type: string | null;
  lineno: number;
  end_lineno: number;
  branch_count: number;
  cyclomatic_complexity: number;
  branches: { type: string; lineno: number; condition: string | null }[];
};

export type StructuredRequirement = {
  requirement_id: string;
  condition: string;
  expected_result: string;
  source_excerpt: string;
};

export type SessionPayload = {
  session_id: string;
  status: string;
  created_at?: string;
  source_code?: string;
  requirements_text?: string;
  inputs?: { original_filename?: string };
  code_analysis?: {
    function_count?: number;
    functions?: FunctionAnalysis[];
  } | null;
  requirement_analysis?: {
    requirement_count?: number;
    requirements?: StructuredRequirement[];
    model?: string;
  } | null;
  errors?: unknown[];
  white_box_tests?: {
    test_count?: number;
    function_count?: number;
    files_written?: string[];
    functions?: {
      function: string;
      status: string;
      source?: string;
      case_count?: number;
      cases?: {
        case_id: string;
        description: string;
        requirement_id?: string;
      }[];
    }[];
  } | null;
};

function apiUrl(path: string): string {
  const base = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '');
  return `${base}${path}`;
}

async function readError(res: Response): Promise<string> {
  const data = await res.json().catch(() => null);
  const detail = data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item: { msg?: string }) => item.msg || JSON.stringify(item)).join('; ');
  }
  return res.statusText || 'Request failed';
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), init);
  if (!res.ok) {
    throw new Error(await readError(res));
  }
  return res.json() as Promise<T>;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const data = await request<{ status: string }>('/api/health');
    return data.status === 'ok';
  } catch {
    return false;
  }
}

export async function fetchExample(): Promise<{
  filename: string;
  source_code: string;
  requirements_text: string;
}> {
  return request('/api/examples');
}

export async function createSession(
  sourceCode: string,
  requirementsText: string,
  filename = 'source.py'
): Promise<SessionPayload> {
  const form = new FormData();
  form.append('source_file', new File([sourceCode], filename, { type: 'text/x-python' }));
  form.append('requirements_text', requirementsText);
  form.append('run_analysis', 'false');
  return request('/api/sessions', { method: 'POST', body: form });
}

export async function runCodeAnalysis(sessionId: string): Promise<SessionPayload> {
  return request(`/api/sessions/${sessionId}/code-analysis`, { method: 'POST' });
}

export async function runRequirementAnalysis(sessionId: string): Promise<SessionPayload> {
  return request(`/api/sessions/${sessionId}/requirement-analysis`, { method: 'POST' });
}

export async function runWhiteBoxTests(sessionId: string): Promise<SessionPayload> {
  return request(`/api/sessions/${sessionId}/white-box-tests`, { method: 'POST' });
}

export async function getSession(sessionId: string): Promise<SessionPayload> {
  return request(`/api/sessions/${sessionId}`);
}

export async function downloadSessionReport(sessionId: string): Promise<void> {
  const res = await fetch(apiUrl(`/api/sessions/${sessionId}/report`));
  if (!res.ok) {
    throw new Error(await readError(res));
  }
  const reportBlob = await res.blob();
  const objectUrl = URL.createObjectURL(reportBlob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = `test-report-${sessionId}.html`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

export function persistSessionId(sessionId: string) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
}

export function readStoredSessionId(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(SESSION_STORAGE_KEY);
}
