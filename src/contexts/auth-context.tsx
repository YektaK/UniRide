
"use client";

import type { User } from "@/types";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import React, { createContext, useState, useEffect } from "react";
import { signIn, signOutUser, onAuthStateChange } from "@/lib/supabase-auth";

interface AuthContextType {
  user: User | null;
  setUser: Dispatch<SetStateAction<User | null>>;
  isLoading: boolean;
  login: (emailOrUsername: string, password_param: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Listen to Firebase Auth state changes
    const unsubscribe = onAuthStateChange((user) => {
      setUser(user);
      setIsLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const login = async (emailOrUsername: string, password_param: string) => {
    setIsLoading(true);
    try {
      const loggedInUser = await signIn(emailOrUsername, password_param);
      if (loggedInUser) {
        setUser(loggedInUser);
      } else {
        throw new Error("Invalid credentials");
      }
    } catch (error) {
      console.error("Login error:", error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await signOutUser();
      setUser(null);
    } catch (error) {
      console.error("Logout error:", error);
      throw error;
    }
  };

  return (
    <AuthContext.Provider value={{ user, setUser, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
