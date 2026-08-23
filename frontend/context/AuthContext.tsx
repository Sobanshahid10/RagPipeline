"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getMe, UserProfile } from "@/lib/api";

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  loginUser: (token: string, userProfile?: UserProfile) => Promise<void>;
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
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const initAuth = async () => {
      try {
        const storedToken = localStorage.getItem("rag_token");
        if (storedToken) {
          setToken(storedToken);
          const profile = await getMe(storedToken);
          setUser(profile);
        }
      } catch (err) {
        console.warn("Session restore failed, logging out:", err);
        localStorage.removeItem("rag_token");
        setToken(null);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const loginUser = async (newToken: string, userProfile?: UserProfile) => {
    localStorage.setItem("rag_token", newToken);
    setToken(newToken);
    if (userProfile) {
      setUser(userProfile);
    } else {
      try {
        const profile = await getMe(newToken);
        setUser(profile);
      } catch (e) {
        console.error("Could not fetch user profile on login:", e);
      }
    }
  };

  const logoutUser = () => {
    localStorage.removeItem("rag_token");
    setToken(null);
    setUser(null);
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
