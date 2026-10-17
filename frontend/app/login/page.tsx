'use client';

import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { getGoogleAuthUrl, loginUser, registerUser } from '@/lib/auth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

type Mode = 'login' | 'register';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get('next') || '/live-lab';

  const [mode, setMode] = useState<Mode>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === 'register') {
        await registerUser(username.trim(), password);
      } else {
        await loginUser(username.trim(), password);
      }
      router.replace(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  }

  async function onGoogle() {
    setError(null);
    setGoogleLoading(true);
    try {
      const { url, state } = await getGoogleAuthUrl();
      sessionStorage.setItem('bugai_oauth_state', state);
      window.location.href = url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google sign-in is not configured.');
      setGoogleLoading(false);
    }
  }

  return (
    <main className="min-h-screen pt-24 pb-16 px-4 flex items-center justify-center">
      <div className="w-full max-w-md rounded-2xl border border-yellow-500/20 bg-black/40 backdrop-blur-xl p-8 shadow-xl shadow-yellow-500/5">
        <h1 className="text-2xl font-bold text-white text-center mb-2">
          {mode === 'login' ? 'Sign in' : 'Create account'}
        </h1>
        <p className="text-sm text-neutral-400 text-center mb-8">
          Use a unique username and password, or continue with Google.
        </p>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username" className="text-neutral-300">Username</Label>
            <Input
              id="username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              maxLength={32}
              className="bg-black/50 border-yellow-500/20"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password" className="text-neutral-300">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              className="bg-black/50 border-yellow-500/20"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400" role="alert">{error}</p>
          )}

          <Button
            type="submit"
            disabled={loading}
            className="w-full bg-yellow-500 text-black hover:bg-yellow-400"
          >
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {mode === 'login' ? 'Sign in' : 'Register'}
          </Button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-yellow-500/15" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-transparent px-2 text-neutral-500">or</span>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          disabled={googleLoading}
          onClick={onGoogle}
          className="w-full border-yellow-500/30 text-white hover:bg-yellow-500/10"
        >
          {googleLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Sign in with Google
        </Button>

        <p className="mt-6 text-center text-sm text-neutral-400">
          {mode === 'login' ? (
            <>
              New here?{' '}
              <button
                type="button"
                className="text-yellow-500 hover:underline"
                onClick={() => setMode('register')}
              >
                Create an account
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button
                type="button"
                className="text-yellow-500 hover:underline"
                onClick={() => setMode('login')}
              >
                Sign in
              </button>
            </>
          )}
        </p>

        <p className="mt-4 text-center">
          <Link href="/" className="text-xs text-neutral-500 hover:text-neutral-300">
            ← Back to home
          </Link>
        </p>
      </div>
    </main>
  );
}
