"use client";

import { Suspense } from "react";
import { useAuth } from "@/lib/auth-context";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

function CallbackHandler() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // API redirects here with ?token=JWT&user={...}
    const token = searchParams.get("token");
    const userJson = searchParams.get("user");

    if (!token || !userJson) {
      setError("Missing authentication data. Please try again.");
      return;
    }

    try {
      const userData = JSON.parse(userJson);
      login(token, {
        id: userData.id,
        username: userData.username,
        avatar: userData.avatar,
        guilds: userData.guilds || [],
      });
      router.push("/dashboard");
    } catch {
      setError("Failed to parse authentication data.");
    }
  }, [searchParams, login, router]);

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="rounded-xl border border-red-500/30 bg-bg-card p-8 text-center">
          <h2 className="mb-2 text-lg font-semibold text-red-400">
            Authentication Error
          </h2>
          <p className="mb-4 text-sm text-muted">{error}</p>
          <a
            href="/login"
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white"
          >
            Try Again
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="text-center">
        <div className="mb-4 h-8 w-8 mx-auto animate-spin rounded-full border-2 border-accent border-t-transparent" />
        <p className="text-sm text-muted">Completing login...</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[60vh] items-center justify-center">
          <div className="text-center">
            <div className="mb-4 h-8 w-8 mx-auto animate-spin rounded-full border-2 border-accent border-t-transparent" />
            <p className="text-sm text-muted">Loading...</p>
          </div>
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
