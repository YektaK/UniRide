
"use client";

import { AuthContext } from "@/contexts/auth-context";
import { useContext } from "react";
import type { User } from "@/types"; // UserRole importu User tipinden gelecek

// Keep the login signature general for now, will be specified in AuthContextType
interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  updateUser: (updatedUser: User) => void;
  login: (emailOrUsername: string, password_param: string) => Promise<void>; // role parametresi kaldırıldı
  logout: () => Promise<void>;
}


export function useAuth() {
  const context = useContext(AuthContext as React.Context<AuthContextType>);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
