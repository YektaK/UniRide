"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global app error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6">
      <h2 className="text-xl font-semibold">Bir hata oluştu</h2>
      <p className="text-sm text-muted-foreground">Lütfen tekrar deneyin.</p>
      <Button onClick={reset}>Tekrar Dene</Button>
    </div>
  );
}
