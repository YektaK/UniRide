
"use client";

import type { User } from "@/types"; // UserRole importu kaldırıldı, User içinde zaten var
import type { Dispatch, ReactNode, SetStateAction } from "react";
import React, { createContext, useState, useEffect } from "react";

interface AuthContextType {
  user: User | null;
  setUser: Dispatch<SetStateAction<User | null>>;
  isLoading: boolean;
  login: (emailOrUsername: string, password_param: string) => void; // role parametresi kaldırıldı
  logout: () => void;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Mock users for demonstration
const mockAdmin: User = {
  id: "admin001",
  name: "Admin Kullanıcısı",
  email: "admin@uniride.com",
  password: "admin", // Şifre "admin" olarak güncellendi
  role: "admin",
  homeAddress: "Üniversite Yönetim Binası",
};

const mockStudent1: User = {
  id: "student001",
  name: "Öğrenci Ayşe",
  email: "student@uniride.com",
  password: "studentpassword",
  role: "student",
  homeAddress: "123 Lale Sokak, Çankaya, Ankara",
  accessibilityNeeds: ["wheelchair"],
  weeklyScheduleId: "schedule001",
};

const mockStudent2: User = {
  id: "student002",
  name: "Öğrenci Veli",
  email: "veli@uniride.com",
  password: "velipassword",
  role: "student",
  homeAddress: "456 Menekşe Caddesi, Yenimahalle, Ankara",
  accessibilityNeeds: [],
  weeklyScheduleId: "schedule002",
};

const mockStudent3: User = {
  id: "student003",
  name: "Öğrenci Zeynep",
  email: "zeynep@uniride.com",
  password: "zeyneppassword",
  role: "student",
  homeAddress: "789 Gül Apartmanı, Keçiören, Ankara",
  accessibilityNeeds: ["visual_impairment"],
  weeklyScheduleId: "schedule003",
};

const allMockUsers = [mockAdmin, mockStudent1, mockStudent2, mockStudent3];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const storedUser = localStorage.getItem("uniRideUser");
    if (storedUser) {
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  const login = (emailOrUsername: string, password_param: string) => { // role parametresi kaldırıldı
    setIsLoading(true);
    setTimeout(() => {
      const lowerEmailOrUsername = emailOrUsername.toLowerCase();
      let loggedInUser: User | null = null;

      if (lowerEmailOrUsername === mockAdmin.email && password_param === mockAdmin.password) {
        loggedInUser = mockAdmin;
      } else {
        // Check against all student users
        const foundStudent = allMockUsers.find(
          u => u.role === 'student' && u.email.toLowerCase() === lowerEmailOrUsername && u.password === password_param
        );
        if (foundStudent) {
          loggedInUser = foundStudent;
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
    // window.location.href = "/login"; 
  };

  return (
    <AuthContext.Provider value={{ user, setUser, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
