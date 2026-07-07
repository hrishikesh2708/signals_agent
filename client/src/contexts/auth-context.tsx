"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api } from "@/lib/api";
import { clearStoredUser, loadStoredUser, storeUser } from "@/lib/auth-storage";
import type { UserResponse } from "@/lib/types";

interface AuthContextValue {
  user: UserResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(() => loadStoredUser());
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const data = await api.me({ redirectOnUnauthorized: false });
      if (data.user) {
        storeUser(data.user);
        setUser(data.user);
      } else {
        clearStoredUser();
        setUser(null);
      }
    } catch {
      clearStoredUser();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      await api.login({ email, password });
      await refresh();
    },
    [refresh],
  );

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      clearStoredUser();
      setUser(null);
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, logout, refresh }),
    [user, loading, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
