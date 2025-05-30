
"use client";

import type { User, UserRole } from "@/types";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import React, { createContext, useState, useEffect } from "react";

interface AuthContextType {
  user: User | null;
  setUser: Dispatch<SetStateAction<User | null>>;
  isLoading: boolean;
  login: (emailOrUsername: string, password_param: string, role: UserRole) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Mock users for demonstration
const mockAdmin: User = {
  id: "admin001",
  name: "Admin Kullanıcısı",
  email: "admin@uniride.com",
  password: "adminpassword", // Added mock password
  role: "admin",
  homeAddress: "Üniversite Yönetim Binası",
};

const mockStudent: User = {
  id: "student001",
  name: "Öğrenci Ayşe",
  email: "student@uniride.com", // Changed for easier testing
  password: "studentpassword", // Added mock password
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

  const login = (emailOrUsername: string, password_param: string, role: UserRole) => {
    setIsLoading(true);
    // Simulate API call
    setTimeout(() => {
      let loggedInUser: User | null = null;
      const lowerEmailOrUsername = emailOrUsername.toLowerCase();

      if (role === "admin" && lowerEmailOrUsername === mockAdmin.email && password_param === mockAdmin.password) {
        loggedInUser = mockAdmin;
      } else if (role === "student" && lowerEmailOrUsername === mockStudent.email && password_param === mockStudent.password) {
        loggedInUser = mockStudent;
      } else if (role === "student" && lowerEmailOrUsername.includes('@')) { 
        // For demo: Allow any student email if password matches a generic one, or specific one for "student@uniride.com"
        // This part is highly simplified for mock purposes.
        // In a real app, you'd query a database.
        if (password_param === "password123" || (lowerEmailOrUsername === mockStudent.email && password_param === mockStudent.password)) {
           loggedInUser = { ...mockStudent, email: lowerEmailOrUsername, name: `Öğrenci ${lowerEmailOrUsername.split('@')[0]}`};
           // If it's the main mock student, ensure all data is correct
           if (lowerEmailOrUsername === mockStudent.email) {
            loggedInUser = mockStudent;
           }
        }
      }


      if (loggedInUser) {
        setUser(loggedInUser);
        localStorage.setItem("uniRideUser", JSON.stringify(loggedInUser));
      } else {
        // Login failed
      }
      setIsLoading(false);
    }, 500);
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem("uniRideUser");
    // Optionally redirect to login page
    // window.location.href = "/login"; 
  };

  return (
    <AuthContext.Provider value={{ user, setUser, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
