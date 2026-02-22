"use client";

import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

const DISCORD_CLIENT_ID = "1475110305099939973";
const REDIRECT_URI = "http://localhost:8000/api/auth/discord/callback";
const DISCORD_AUTH_URL = `https://discord.com/api/oauth2/authorize?client_id=${DISCORD_CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&response_type=code&scope=identify%20guilds`;

export default function LoginPage() {
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) router.push("/dashboard");
  }, [user, router]);

  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="w-full max-w-md rounded-xl border border-border bg-bg-card p-8 text-center">
        <div className="mb-6">
          <h1 className="text-2xl font-bold">
            <span className="bg-gradient-to-r from-accent to-cyan-400 bg-clip-text text-transparent">
              NeuroWeave
            </span>
          </h1>
          <p className="mt-2 text-sm text-muted">
            Sign in to manage your servers and knowledge base
          </p>
        </div>

        <a
          href={DISCORD_AUTH_URL}
          className="flex w-full items-center justify-center gap-3 rounded-lg bg-[#5865F2] px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#4752C4]"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20.317 4.37a19.791 19.791 0 00-4.885-1.515.074.074 0 00-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 00-5.487 0 12.64 12.64 0 00-.617-1.25.077.077 0 00-.079-.037A19.736 19.736 0 003.677 4.37a.07.07 0 00-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 00.031.057 19.9 19.9 0 005.993 3.03.078.078 0 00.084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 00-.041-.106 13.107 13.107 0 01-1.872-.892.077.077 0 01-.008-.128 10.2 10.2 0 00.372-.292.074.074 0 01.077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 01.078.01c.12.098.246.198.373.292a.077.077 0 01-.006.127 12.299 12.299 0 01-1.873.892.077.077 0 00-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 00.084.028 19.839 19.839 0 006.002-3.03.077.077 0 00.032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 00-.031-.03z" />
          </svg>
          Login with Discord
        </a>

        <p className="mt-6 text-xs text-dim">
          We only request access to your Discord username and server list.
          No messages are read through OAuth.
        </p>
      </div>
    </div>
  );
}
