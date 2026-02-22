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
      <div className="mb-8">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="mt-1 text-muted">
          Manage your servers, channels, and knowledge base
        </p>
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
