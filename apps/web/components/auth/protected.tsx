"use client";

import { useRouter } from "next/navigation";
import * as React from "react";

import { useAuth } from "@/lib/auth-context";

/** Client-side route guard. Redirects to /login if no user. */
export function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  React.useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Ładowanie...
      </div>
    );
  }

  return <>{children}</>;
}
