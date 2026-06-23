"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  clearStoredAuth,
  fetchCurrentUser,
  getStoredAccessToken,
  getStoredUser,
  linkAnonymousContributions,
  loginRequest,
  registerRequest,
  saveAuth,
} from "@/lib/api";
import type { AuthUser } from "@/lib/types";

type AuthContextValue = {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: { email: string; password: string }) => Promise<AuthUser>;
  register: (payload: { email: string; username: string; password: string }) => Promise<AuthUser>;
  logout: () => void;
  refreshAuth: () => Promise<AuthUser | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const restoreAnonymousContributions = useCallback(async () => {
    const anonymousToken = localStorage.getItem("anonymous_token");
    if (!anonymousToken) return;

    try {
      await linkAnonymousContributions(anonymousToken);
      localStorage.removeItem("anonymous_token");
    } catch {
      // Linking is best-effort; auth should not fail because of old anonymous donations.
    }
  }, []);

  const refreshAuth = useCallback(async () => {
    if (!getStoredAccessToken()) {
      setUser(null);
      return null;
    }

    try {
      const currentUser = await fetchCurrentUser();
      localStorage.setItem("auth_user", JSON.stringify(currentUser));
      setUser(currentUser);
      return currentUser;
    } catch {
      clearStoredAuth();
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    const storedUser = getStoredUser();
    if (storedUser) {
      setUser(storedUser);
    }

    refreshAuth().finally(() => setIsLoading(false));

    function handleLogout() {
      setUser(null);
    }

    function handleAuthUpdated(event: Event) {
      setUser((event as CustomEvent<AuthUser>).detail);
    }

    window.addEventListener("auth:logout", handleLogout);
    window.addEventListener("auth:updated", handleAuthUpdated);

    return () => {
      window.removeEventListener("auth:logout", handleLogout);
      window.removeEventListener("auth:updated", handleAuthUpdated);
    };
  }, [refreshAuth]);

  const login = useCallback(
    async (payload: { email: string; password: string }) => {
      const auth = await loginRequest(payload);
      saveAuth(auth);
      setUser(auth.user);
      await restoreAnonymousContributions();
      return auth.user;
    },
    [restoreAnonymousContributions],
  );

  const register = useCallback(
    async (payload: { email: string; username: string; password: string }) => {
      const auth = await registerRequest(payload);
      saveAuth(auth);
      setUser(auth.user);
      await restoreAnonymousContributions();
      return auth.user;
    },
    [restoreAnonymousContributions],
  );

  const logout = useCallback(() => {
    clearStoredAuth();
    setUser(null);
    router.push("/");
  }, [router]);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      login,
      register,
      logout,
      refreshAuth,
    }),
    [isLoading, login, logout, refreshAuth, register, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
