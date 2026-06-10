'use client';

import React, { createContext, useState, useContext, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// Subscription tier type
export type UserTier = 'free' | 'pro';

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  tier: UserTier; // Added for subscription support
}

interface AuthContextType {
  user: User | null;
  accessToken: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  isLoading: boolean;
  // New tier-related helpers
  isPro: boolean;
  tier: UserTier;
  upgradeToPro: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  // Load user from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('smartbet_access_token');
    const storedUser = localStorage.getItem('smartbet_user');

    if (storedToken && storedUser) {
      setAccessToken(storedToken);
      setUser(JSON.parse(storedUser));
    }

    setIsLoading(false);
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/auth/login/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Login failed');
      }

      // Store tokens and user
      localStorage.setItem('smartbet_access_token', data.tokens.access);
      localStorage.setItem('smartbet_refresh_token', data.tokens.refresh);
      localStorage.setItem('smartbet_user', JSON.stringify(data.user));

      // Remove old session_id if exists
      localStorage.removeItem('smartbet_session_id');

      setAccessToken(data.tokens.access);
      setUser(data.user);

      router.push('/');
    } catch (error: any) {
      throw new Error(error.message || 'Login failed');
    }
  };

  const register = async (username: string, email: string, password: string) => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/auth/register/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Registration failed');
      }

      // Store tokens and user
      localStorage.setItem('smartbet_access_token', data.tokens.access);
      localStorage.setItem('smartbet_refresh_token', data.tokens.refresh);
      localStorage.setItem('smartbet_user', JSON.stringify(data.user));

      // Remove old session_id if exists
      localStorage.removeItem('smartbet_session_id');

      setAccessToken(data.tokens.access);
      setUser(data.user);

      router.push('/');
    } catch (error: any) {
      throw new Error(error.message || 'Registration failed');
    }
  };

  const logout = () => {
    // Clear tokens and user
    localStorage.removeItem('smartbet_access_token');
    localStorage.removeItem('smartbet_refresh_token');
    localStorage.removeItem('smartbet_user');
    localStorage.removeItem('smartbet_bankroll');

    setAccessToken(null);
    setUser(null);

    router.push('/login');
  };

  // Upgrade user to Pro tier (called after successful payment)
  const upgradeToPro = async () => {
    if (!user) return;

    const updatedUser = { ...user, tier: 'pro' as UserTier };
    setUser(updatedUser);
    localStorage.setItem('smartbet_user', JSON.stringify(updatedUser));

    // In production, also call API to update user tier in database
    // await fetch(`${apiUrl}/api/auth/upgrade/`, { ... })
  };

  // Determine current tier (default to 'free' if not set)
  const currentTier: UserTier = user?.tier || 'free';

  const value = {
    user,
    accessToken,
    login,
    register,
    logout,
    isAuthenticated: !!user,
    isLoading,
    // Tier-related properties
    isPro: currentTier === 'pro',
    tier: currentTier,
    upgradeToPro,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

