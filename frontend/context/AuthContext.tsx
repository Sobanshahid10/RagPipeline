"use client";

import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getMe, UserProfile } from "@/lib/api";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  loginUser: (token: string) => Promise<void>;
  logoutUser: () => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  isLoading: true,
  loginUser: async () => {},
  logoutUser: () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const authAttempt = useRef(0);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const attempt = ++authAttempt.current;
    try {
      localStorage.removeItem("rag_chat_sessions");
      localStorage.removeItem("rag_token");
    } catch { /* Authentication still works if browser storage is unavailable. */ }
    const initAuth = async () => {
      try {
        const storedToken = sessionStorage.getItem("rag_token");
        if (storedToken) {
          const profile = await getMe(storedToken);
          if (attempt !== authAttempt.current) return;
          setUser(profile);
          setToken(storedToken);
        }
      } catch {
        if (attempt !== authAttempt.current) return;
        try { sessionStorage.removeItem("rag_token"); } catch { /* Storage unavailable. */ }
        setToken(null);
        setUser(null);
      } finally {
        if (attempt === authAttempt.current) setIsLoading(false);
      }
    };
    void initAuth();
    return () => { authAttempt.current += 1; };
  }, []);

  const loginUser = async (newToken: string) => {
    const attempt = ++authAttempt.current;
    setIsLoading(true);
    setToken(null);
    setUser(null);
    try {
      const profile = await getMe(newToken);
      if (attempt !== authAttempt.current) throw new Error("Sign-in was cancelled");
      try { sessionStorage.setItem("rag_token", newToken); } catch { /* Use this in-memory session. */ }
      setUser(profile);
      setToken(newToken);
    } catch (error) {
      if (attempt === authAttempt.current) {
        try { sessionStorage.removeItem("rag_token"); } catch { /* Storage unavailable. */ }
        setToken(null);
        setUser(null);
      }
      throw error;
    } finally {
      if (attempt === authAttempt.current) setIsLoading(false);
    }
  };

  const logoutUser = () => {
    authAttempt.current += 1;
    try { sessionStorage.removeItem("rag_token"); } catch { /* Clear in-memory identity too. */ }
    setToken(null);
    setUser(null);
    setIsLoading(false);
    router.push("/login");
  };

  // Route guard
  useEffect(() => {
    if (!isLoading) {
      const isAuthRoute = pathname?.startsWith("/login");

      if (!token && !isAuthRoute) {
        router.push("/login");
      } else if (token && isAuthRoute) {
        router.push("/chat");
      }
    }
  }, [token, isLoading, pathname, router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        loginUser,
        logoutUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
