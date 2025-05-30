
"use client";

import { AuthContext } from "@/contexts/auth-context";
import { useContext } from "react";
import type { User } from "@/types"; // UserRole importu User tipinden gelecek

// Keep the login signature general for now, will be specified in AuthContextType
interface AuthContextType {
  user: User | null;
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
  isLoading: boolean;
  login: (emailOrUsername: string, password_param: string) => void; // role parametresi kaldırıldı
  logout: () => void;
}


export function useAuth() {
  const context = useContext(AuthContext as React.Context<AuthContextType>);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
