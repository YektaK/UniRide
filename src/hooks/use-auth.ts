
"use client";

import { AuthContext } from "@/contexts/auth-context";
import { useContext } from "react";

// Keep the login signature general for now, will be specified in AuthContextType
interface AuthContextType {
  user: import("@/types").User | null;
  setUser: React.Dispatch<React.SetStateAction<import("@/types").User | null>>;
  isLoading: boolean;
  login: (emailOrUsername: string, password_param: string, role: import("@/types").UserRole) => void;
  logout: () => void;
}


export function useAuth() {
  const context = useContext(AuthContext as React.Context<AuthContextType>);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
