"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <nav className="sticky top-0 z-50 border-b border-border bg-bg/80 backdrop-blur-lg">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-xl font-bold bg-gradient-to-r from-accent to-cyan-400 bg-clip-text text-transparent">
            NeuroWeave
          </span>
        </Link>

        <div className="flex items-center gap-6">
          <Link
            href="/search"
            className="text-sm text-muted hover:text-white transition-colors"
          >
            Search
          </Link>
          <Link
            href="/"
            className="text-sm text-muted hover:text-white transition-colors"
          >
            Servers
          </Link>

          {user ? (
            <div className="flex items-center gap-3">
              <Link
                href="/dashboard"
                className="text-sm text-muted hover:text-white transition-colors"
              >
                Dashboard
              </Link>
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-accent/20 text-xs font-bold text-accent">
                  {user.username.charAt(0).toUpperCase()}
                </div>
                <span className="text-sm text-muted">{user.username}</span>
              </div>
              <button
                onClick={logout}
                className="rounded-lg border border-border px-3 py-1.5 text-xs text-dim hover:border-red-500/50 hover:text-red-400 transition-colors"
              >
                Logout
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="rounded-lg bg-accent px-4 py-1.5 text-sm font-medium text-white hover:bg-accent-hover transition-colors"
            >
              Login
            </Link>
          )}
        </div>
      </div>
    </nav>
  );
}
