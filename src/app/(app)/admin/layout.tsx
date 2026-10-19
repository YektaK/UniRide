
"use client";

/**
 * Admin Layout — Rol Koruması (P0-2 Fix)
 *
 * Tüm /admin/* route'larını tek noktadan korur.
 * Admin olmayan kullanıcılar home sayfasına yönlendirilir.
 * API katmanı zaten requireAdmin ile korunuyor; bu UI katmanı savunmasıdır.
 */

import type { ReactNode } from "react";
import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

interface AdminLayoutProps {
  children: ReactNode;
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const isAdmin = !!user && user.role === "admin";

  // Admin değilse ana sayfaya yönlendir (render sırasında değil, effect içinde)
  useEffect(() => {
    if (!isLoading && !isAdmin) {
      router.replace("/");
    }
  }, [isLoading, isAdmin, router]);

  // Kimlik doğrulama yüklenirken bekle
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-muted-foreground text-sm">Yetki kontrol ediliyor...</div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-destructive text-sm">Erişim reddedildi. Yönlendiriliyor...</div>
      </div>
    );
  }

  // Admin ise içeriği göster
  return <>{children}</>;
}
