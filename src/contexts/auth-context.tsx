
"use client";

import type { User } from "@/types";
import type { ReactNode } from "react";
import React, { createContext, useState, useEffect } from "react";
import { signIn, signOutUser, onAuthStateChange } from "@/lib/supabase-auth";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  updateUser: (updatedUser: User) => void;
  login: (emailOrUsername: string, password_param: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Listen to Supabase Auth state changes
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

  const updateUser = (updatedUser: User) => {
    setUser((currentUser) => {
      if (!currentUser || currentUser.id !== updatedUser.id) {
        return currentUser;
      }

      return {
        ...currentUser,
        name: updatedUser.name,
        homeAddress: updatedUser.homeAddress,
        homeCoordinates: updatedUser.homeCoordinates,
        accessibilityNeeds: updatedUser.accessibilityNeeds,
        disabilityType: updatedUser.disabilityType,
        locationCode: updatedUser.locationCode,
        weeklyScheduleId: updatedUser.weeklyScheduleId,
        passwordHint: updatedUser.passwordHint,
      };
    });
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, updateUser, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
