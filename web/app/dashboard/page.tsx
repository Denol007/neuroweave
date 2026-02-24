"use client";

import { useAuth } from "@/lib/auth-context";
import { getServers, type Server } from "@/lib/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function DashboardPage() {
  const { user, token } = useAuth();
  const router = useRouter();
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) {
      router.push("/login");
      return;
    }
    getServers()
      .then(setServers)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user, router]);

  if (!user) return null;

  return (
    <div>
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="mt-1 text-muted">
            Manage your servers, channels, and knowledge base
          </p>
        </div>
        <Link
          href="/dashboard/github"
          className="rounded-lg border border-border bg-bg-card px-4 py-2 text-sm text-muted hover:border-white hover:text-white transition-colors flex items-center gap-2"
        >
          <svg className="h-4 w-4" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
          </svg>
          GitHub Repos
        </Link>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        </div>
      ) : servers.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {servers.map((server) => (
            <Link
              key={server.id}
              href={`/dashboard/${server.id}`}
              className="group rounded-xl border border-border bg-bg-card p-6 transition-all hover:-translate-y-0.5 hover:border-accent/50 hover:shadow-lg hover:shadow-accent/5"
            >
              <div className="mb-4 flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/20 text-lg font-bold text-accent">
                  {server.name.charAt(0)}
                </div>
                <div>
                  <h3 className="font-semibold group-hover:text-accent-hover transition-colors">
                    {server.name}
                  </h3>
                  <p className="text-xs text-dim">
                    {server.member_count.toLocaleString()} members
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="rounded bg-white/[0.04] px-2 py-0.5 font-mono text-xs text-muted">
                  {server.plan}
                </span>
                <span className="text-xs text-accent group-hover:translate-x-1 transition-transform">
                  Manage &rarr;
                </span>
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted">
          <p className="mb-2 text-lg">No servers found</p>
          <p className="text-sm text-dim">
            Add the NeuroWeave bot to your Discord server to get started.
          </p>
        </div>
      )}
    </div>
  );
}
