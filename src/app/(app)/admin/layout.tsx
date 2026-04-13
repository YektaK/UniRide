
"use client";

/**
 * Admin Layout — Rol Koruması (P0-2 Fix)
 *
 * Tüm /admin/* route'larını tek noktadan korur.
 * Admin olmayan kullanıcılar home sayfasına yönlendirilir.
 * API katmanı zaten requireAdmin ile korunuyor; bu UI katmanı savunmasıdır.
 */

import type { ReactNode } from "react";
import React from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

interface AdminLayoutProps {
  children: ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  // Kimlik doğrulama yüklenirken bekle
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-muted-foreground text-sm">Yetki kontrol ediliyor...</div>
      </div>
    );
  }

  // Admin değilse ana sayfaya yönlendir
  if (!user || user.role !== "admin") {
    router.replace("/");
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-destructive text-sm">Erişim reddedildi. Yönlendiriliyor...</div>
      </div>
    );
  }

  // Admin ise içeriği göster
  return <>{children}</>;
}
