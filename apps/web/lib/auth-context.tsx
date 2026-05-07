"use client";

import { useRouter } from "next/navigation";
import * as React from "react";

import { authApi, HttpError } from "./api-client";
import type { UserResponse } from "./api-types";

interface AuthContextValue {
  user: UserResponse | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<UserResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const router = useRouter();

  React.useEffect(() => {
    let mounted = true;
    authApi
      .me()
      .then((u) => {
        if (mounted) setUser(u);
      })
      .catch((err) => {
        if (err instanceof HttpError && err.status === 401) {
          // Not logged in — that's fine, login page will handle.
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  const login = React.useCallback(
    async (username: string, password: string) => {
      const u = await authApi.login({ username, password });
      setUser(u);
      router.push("/");
    },
    [router],
  );

  const logout = React.useCallback(async () => {
    await authApi.logout();
    setUser(null);
    router.push("/login");
  }, [router]);

  const value = React.useMemo(
    () => ({ user, loading, login, logout }),
    [user, loading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
