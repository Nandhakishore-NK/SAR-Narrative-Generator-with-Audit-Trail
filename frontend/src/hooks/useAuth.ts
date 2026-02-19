/**
 * SAR Guardian — Auth Hook
 * Manages authentication state with localStorage persistence.
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import type { User, TokenResponse, LoginCredentials } from "@/types";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    // Hydrate user from localStorage
    const stored = localStorage.getItem("sar_user");
    const token = localStorage.getItem("sar_token");
    if (stored && token) {
      try {
        setUser(JSON.parse(stored));
      } catch {
        localStorage.removeItem("sar_user");
        localStorage.removeItem("sar_token");
      }
    }
    setLoading(false);
  }, []);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      const { data } = await api.post<TokenResponse>(
        "/api/auth/login",
        credentials
      );
      localStorage.setItem("sar_token", data.access_token);
      localStorage.setItem("sar_user", JSON.stringify(data.user));
      setUser(data.user);
      router.push("/dashboard");
    },
    [router]
  );

  const logout = useCallback(() => {
    localStorage.removeItem("sar_token");
    localStorage.removeItem("sar_user");
    setUser(null);
    router.push("/login");
  }, [router]);

  return { user, loading, login, logout };
}
