'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { forgotPasswordAction, loginAction, resetPasswordAction } from '@/lib/auth-actions';
import { Loader2 } from 'lucide-react';

type AuthMode = 'login' | 'forgot' | 'reset';

export default function LoginPage() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [mode, setMode] = useState<AuthMode>('login');
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [resetToken, setResetToken] = useState<string>('');

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const formData = new FormData(event.currentTarget);

    startTransition(async () => {
      const result = await loginAction(formData);
      if (result.success) {
        router.push('/dashboard');
        router.refresh();
      } else {
        setError(result.message ?? 'Login failed. Please try again.');
      }
    });
  }

  async function handleForgotSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const formData = new FormData(event.currentTarget);

    startTransition(async () => {
      const result = await forgotPasswordAction(formData);
      if (!result.success) {
        setError(result.message ?? 'Could not start password reset.');
        return;
      }

      setMessage(result.message ?? 'Password reset started.');
      if (result.resetToken) {
        setResetToken(result.resetToken);
        setMode('reset');
      }
    });
  }

  async function handleResetSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);

    const formData = new FormData(event.currentTarget);

    startTransition(async () => {
      const result = await resetPasswordAction(formData);
      if (result.success) {
        setResetToken('');
        setMode('login');
        setMessage(result.message ?? 'Password reset. Please sign in.');
      } else {
        setError(result.message ?? 'Could not reset password.');
      }
    });
  }

  const title = mode === 'login' ? 'Sign in' : mode === 'forgot' ? 'Forgot password' : 'Reset password';
  const subtitle = mode === 'login'
    ? 'Enter your credentials to access the admin panel'
    : mode === 'forgot'
      ? 'Enter your email to generate a reset token'
      : 'Enter your new password';

  return (
    <div className="min-h-screen flex items-center justify-center bg-stone-50">
      <div className="w-full max-w-sm px-4">
        {/* Wordmark */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-stone-900 tracking-tight">
            BeHazeld OS
          </h1>
          <p className="text-sm text-stone-500 mt-1">Admin Portal</p>
        </div>

        <Card className="shadow-sm border-stone-200">
          <CardHeader className="pb-4">
            <h2 className="text-lg font-semibold text-stone-800">{title}</h2>
            <p className="text-sm text-stone-500">
              {subtitle}
            </p>
          </CardHeader>
          <CardContent>
            {mode === 'login' ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-stone-700">
                  Email
                </Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="you@behazeld.com"
                  className="border-stone-300 focus-visible:ring-rose-800"
                  disabled={isPending}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-stone-700">
                  Password
                </Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  placeholder="••••••••"
                  className="border-stone-300 focus-visible:ring-rose-800"
                  disabled={isPending}
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  className="text-sm text-rose-800 hover:text-rose-900 hover:underline"
                  disabled={isPending}
                  onClick={() => {
                    setError(null);
                    setMessage(null);
                    setMode('forgot');
                  }}
                >
                  Forgot password?
                </button>
              </div>

              {error && (
                <p className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-2">
                  {error}
                </p>
              )}
              {message && (
                <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-md px-3 py-2">
                  {message}
                </p>
              )}

              <Button
                type="submit"
                disabled={isPending}
                className="w-full bg-rose-800 hover:bg-rose-900 text-white"
              >
                {isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing in…
                  </>
                ) : (
                  'Sign in'
                )}
              </Button>
            </form>
            ) : mode === 'forgot' ? (
            <form onSubmit={handleForgotSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="reset-email" className="text-stone-700">
                  Email
                </Label>
                <Input
                  id="reset-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="you@behazeld.com"
                  className="border-stone-300 focus-visible:ring-rose-800"
                  disabled={isPending}
                />
              </div>

              {error && (
                <p className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-2">
                  {error}
                </p>
              )}
              {message && (
                <p className="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-md px-3 py-2">
                  {message}
                </p>
              )}

              <Button
                type="submit"
                disabled={isPending}
                className="w-full bg-rose-800 hover:bg-rose-900 text-white"
              >
                {isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Generating…
                  </>
                ) : (
                  'Generate reset token'
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={isPending}
                className="w-full"
                onClick={() => {
                  setError(null);
                  setMessage(null);
                  setMode('login');
                }}
              >
                Back to sign in
              </Button>
            </form>
            ) : (
            <form onSubmit={handleResetSubmit} className="space-y-4">
              <input type="hidden" name="reset_token" value={resetToken} />
              {resetToken && (
                <p className="break-all rounded-md border border-stone-200 bg-stone-50 px-3 py-2 text-xs text-stone-500">
                  Reset token generated. This temporary token is valid for 30 minutes.
                </p>
              )}

              <div className="space-y-1.5">
                <Label htmlFor="new-password" className="text-stone-700">
                  New Password
                </Label>
                <Input
                  id="new-password"
                  name="new_password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  placeholder="Minimum 8 characters"
                  className="border-stone-300 focus-visible:ring-rose-800"
                  disabled={isPending}
                />
              </div>

              {error && (
                <p className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-md px-3 py-2">
                  {error}
                </p>
              )}

              <Button
                type="submit"
                disabled={isPending || !resetToken}
                className="w-full bg-rose-800 hover:bg-rose-900 text-white"
              >
                {isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Resetting…
                  </>
                ) : (
                  'Reset password'
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={isPending}
                className="w-full"
                onClick={() => {
                  setError(null);
                  setMessage(null);
                  setResetToken('');
                  setMode('login');
                }}
              >
                Back to sign in
              </Button>
            </form>
            )}
          </CardContent>
        </Card>

        <p className="text-center text-xs text-stone-400 mt-6">
          BeHazeld E-Commerce OS · Admin v7
        </p>
      </div>
    </div>
  );
}
