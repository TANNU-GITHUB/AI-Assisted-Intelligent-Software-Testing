'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import Link from 'next/link';
import { completeGitHubOAuth } from '@/lib/auth';

export default function GitHubCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const stored = sessionStorage.getItem('bugai_github_oauth_state');

    if (!code || !state) {
      setError('Missing authorization code from GitHub.');
      return;
    }
    if (!stored || stored !== state) {
      setError('Invalid OAuth state. Sign in and connect GitHub again.');
      return;
    }

    sessionStorage.removeItem('bugai_github_oauth_state');

    completeGitHubOAuth(code, state)
      .then(() => router.replace('/live-lab'))
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'GitHub connect failed.');
      });
  }, [router, searchParams]);

  if (error) {
    return (
      <main className="min-h-screen pt-24 px-4 flex flex-col items-center justify-center gap-4">
        <p className="text-red-400 text-center max-w-md">{error}</p>
        <Link href="/live-lab" className="text-yellow-500 hover:underline">
          Return to Live Lab
        </Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen pt-24 flex flex-col items-center justify-center gap-3 text-neutral-300">
      <Loader2 className="h-8 w-8 animate-spin text-yellow-500" />
      <p>Connecting GitHub…</p>
    </main>
  );
}
