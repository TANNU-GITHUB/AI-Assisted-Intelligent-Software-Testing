'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { completeGoogleOAuth } from '@/lib/auth';
import Link from 'next/link';

export default function GoogleCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const stored = sessionStorage.getItem('bugai_oauth_state');

    if (!code || !state) {
      setError('Missing authorization code from Google.');
      return;
    }
    if (!stored || stored !== state) {
      setError('Invalid OAuth state. Please try signing in again.');
      return;
    }

    sessionStorage.removeItem('bugai_oauth_state');

    completeGoogleOAuth(code, state)
      .then(() => router.replace('/live-lab'))
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Google sign-in failed.');
      });
  }, [router, searchParams]);

  if (error) {
    return (
      <main className="min-h-screen pt-24 px-4 flex flex-col items-center justify-center gap-4">
        <p className="text-red-400 text-center max-w-md">{error}</p>
        <Link href="/login" className="text-yellow-500 hover:underline">
          Return to sign in
        </Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen pt-24 flex flex-col items-center justify-center gap-3 text-neutral-300">
      <Loader2 className="h-8 w-8 animate-spin text-yellow-500" />
      <p>Completing Google sign-in…</p>
    </main>
  );
}
