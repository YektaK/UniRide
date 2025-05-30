
"use client";

import type { User, UserRole } from "@/types";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import React, { createContext, useState, useEffect } from "react";

interface AuthContextType {
  user: User | null;
  setUser: Dispatch<SetStateAction<User | null>>;
  isLoading: boolean;
  login: (email: string, role: UserRole) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Mock users for demonstration
const mockAdmin: User = {
  id: "admin001",
  name: "Admin Kullanıcısı",
  email: "admin@uniride.com",
  role: "admin",
  homeAddress: "Üniversite Yönetim Binası",
};

const mockStudent: User = {
  id: "student001",
  name: "Öğrenci Ayşe",
  email: "ayse@example.com",
  role: "student",
  homeAddress: "123 Lale Sokak, Çankaya, Ankara",
  accessibilityNeeds: ["wheelchair"],
  weeklyScheduleId: "schedule001",
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate checking for an existing session
    const storedUser = localStorage.getItem("uniRideUser");
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  const login = (email: string, role: UserRole) => {
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      let loggedInUser: User | null = null;
      if (role === "admin" && email.toLowerCase() === "admin@uniride.com") {
        loggedInUser = mockAdmin;
      } else if (role === "student" && email.toLowerCase() === "student@uniride.com") {
        loggedInUser = mockStudent;
      } else if (role === "student") { // Allow any student email for demo
        loggedInUser = { ...mockStudent, email, name: `Öğrenci ${email.split('@')[0]}`};
      }


      if (loggedInUser) {
        setUser(loggedInUser);
        localStorage.setItem("uniRideUser", JSON.stringify(loggedInUser));
      } else {
        // Handle login failure (e.g., show error message)
        console.error("Login failed: Invalid credentials or role.");
      }
      setIsLoading(false);
    }, 500);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("uniRideUser");
  };

  return (
    <AuthContext.Provider value={{ user, setUser, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
