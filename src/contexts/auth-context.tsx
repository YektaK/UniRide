
"use client";

import type { User } from "@/types";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import React, { createContext, useState, useEffect } from "react";
import { getUserByEmailOrStudentNumber } from "@/lib/mock-database"; // Import from mock DB

interface AuthContextType {
  user: User | null;
  setUser: Dispatch<SetStateAction<User | null>>;
  isLoading: boolean;
  login: (emailOrUsername: string, password_param: string) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedUser = localStorage.getItem("uniRideUser");
    if (storedUser) {
      try {
        const parsedUser = JSON.parse(storedUser);
        // Optional: You might want to re-verify this user against the mock-database
        // or a real backend in a production app for security.
        setUser(parsedUser);
      } catch (error) {
        console.error("Failed to parse user from localStorage", error);
        localStorage.removeItem("uniRideUser");
      }
    }
    setIsLoading(false);
  }, []);

  const login = (emailOrUsername: string, password_param: string) => {
    setIsLoading(true);
    setTimeout(() => {
      const loggedInUser = getUserByEmailOrStudentNumber(emailOrUsername, password_param);
      
      if (loggedInUser) {
        setUser(loggedInUser);
        localStorage.setItem("uniRideUser", JSON.stringify(loggedInUser));
      } else {
        // Handle login failure (e.g., show error message via toast, which is handled in LoginForm)
        // console.error("Login failed: Invalid credentials."); // Original console error, now handled by toast
      }
      setIsLoading(false);
    }, 500);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("uniRideUser");
    // Optionally redirect to login page or home page
    // For example, if using Next.js router: router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, setUser, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
