'use client';

import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import Link from 'next/link';
import { Check } from 'lucide-react';
import Image from 'next/image';
import { getCopy } from '../lib/terminology';
import { track } from '../lib/analytics';
import { useLanguage } from '../contexts/LanguageContext';

export default function RegisterPage() {
  const { language } = useLanguage();
  const copy = getCopy(language);

  useEffect(() => {
    track('registration_started', { surface: 'register' });
  }, []);

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  // Client-side validation errors belong next to the field that caused them.
  // Both used to render in the banner above the form, which on a phone is off
  // screen by the time you are typing the confirmation.
  const [fieldError, setFieldError] = useState<{ password?: string; confirmPassword?: string }>({});
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setFieldError({});

    // Validation
    if (password.length < 8) {
      setFieldError({ password: 'Password must be at least 8 characters long' });
      document.getElementById('password')?.focus();
      return;
    }

    if (password !== confirmPassword) {
      setFieldError({ confirmPassword: 'Passwords do not match' });
      document.getElementById('confirmPassword')?.focus();
      return;
    }

    setIsLoading(true);

    try {
      await register(username, email, password);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <div className="relative w-20 h-20 mb-4 mx-auto">
            <Image
              src="/images/logo-final-v6.png"
              alt="BetGlitch"
              fill
              className="object-contain drop-shadow-md"
            />
          </div>
          <p className="mb-3 inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-bold uppercase tracking-widest text-blue-700">
            {copy.hero.eyebrow}
          </p>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            {copy.register.heading}
          </h1>
          <p className="text-gray-600">
            {copy.register.supporting}
          </p>

          {/* What signing up actually commits you to. Stated before the form,
              not buried under it. */}
          <ul className="mx-auto mt-5 max-w-xs space-y-2 text-left">
            {[
              copy.register.freeDuringBeta,
              copy.register.noPayment,
              copy.register.informational,
            ].map((line) => (
              <li key={line} className="flex items-start gap-2 text-sm text-gray-700">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" aria-hidden="true" />
                <span>{line}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Register Form */}
        <div className="bg-white rounded-lg shadow-lg p-8">
          {error && (
            <div
              role="alert"
              className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm"
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full min-h-[44px] px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Choose a username"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full min-h-[44px] px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="your@email.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                aria-invalid={Boolean(fieldError.password)}
                aria-describedby={fieldError.password ? 'password-error' : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full min-h-[44px] px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="At least 8 characters"
              />
              {fieldError.password && (
                <p id="password-error" role="alert" className="mt-2 text-sm text-red-700">
                  {fieldError.password}
                </p>
              )}
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 mb-2">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                aria-invalid={Boolean(fieldError.confirmPassword)}
                aria-describedby={fieldError.confirmPassword ? 'confirm-error' : undefined}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="w-full min-h-[44px] px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Confirm your password"
              />
              {fieldError.confirmPassword && (
                <p id="confirm-error" role="alert" className="mt-2 text-sm text-red-700">
                  {fieldError.confirmPassword}
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full min-h-[48px] px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400 font-medium focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
            >
              {isLoading ? copy.register.submitting : copy.register.submit}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <Link href="/login" className="text-blue-600 hover:text-blue-700 font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>

        <div className="mt-4 text-center">
          <Link href="/" className="inline-flex min-h-[44px] items-center justify-center px-3 text-sm text-gray-600 hover:text-gray-900">
            ← Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}

