"use client";

import { useAuth } from "@/lib/auth-context";
import { addGitHubRepo, deleteGitHubRepo, getGitHubRepos, syncGitHubRepo } from "@/lib/api";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function GitHubDashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [repos, setRepos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [owner, setOwner] = useState("");
  const [repo, setRepo] = useState("");
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    if (!user) { router.push("/login"); return; }
    loadRepos();
  }, [user, router]);

  const loadRepos = () => {
    getGitHubRepos()
      .then(setRepos)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  const handleAdd = async () => {
    if (!owner || !repo) return;
    setAdding(true);
    try {
      await addGitHubRepo(owner, repo);
      setOwner("");
      setRepo("");
      loadRepos();
    } catch {
    } finally {
      setAdding(false);
    }
  };

  const handleSync = async (id: number) => {
    try {
      await syncGitHubRepo(id);
    } catch {}
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteGitHubRepo(id);
      setRepos((prev) => prev.filter((r) => r.id !== id));
    } catch {}
  };

  if (!user) return null;

  return (
    <div>
      <div className="mb-8">
        <button onClick={() => router.push("/dashboard")} className="mb-2 text-sm text-muted hover:text-white transition-colors">
          &larr; Back to dashboard
        </button>
        <h1 className="text-3xl font-bold">GitHub Repositories</h1>
        <p className="mt-1 text-muted">Connect GitHub repos to extract knowledge from Discussions</p>
      </div>

      {/* Add repo form */}
      <div className="mb-8 rounded-xl border border-border bg-bg-card p-6">
        <h2 className="mb-4 text-lg font-semibold">Add Repository</h2>
        <div className="flex gap-3">
          <input
            type="text"
            placeholder="Owner (e.g. vercel)"
            value={owner}
            onChange={(e) => setOwner(e.target.value)}
            className="flex-1 rounded-lg border border-border bg-bg px-4 py-2 text-sm text-white placeholder:text-dim outline-none focus:border-accent"
          />
          <input
            type="text"
            placeholder="Repo (e.g. next.js)"
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            className="flex-1 rounded-lg border border-border bg-bg px-4 py-2 text-sm text-white placeholder:text-dim outline-none focus:border-accent"
          />
          <button
            onClick={handleAdd}
            disabled={adding || !owner || !repo}
            className="rounded-lg bg-accent px-6 py-2 text-sm font-medium text-white hover:bg-accent-hover transition-colors disabled:opacity-50"
          >
            {adding ? "Adding..." : "Add"}
          </button>
        </div>
      </div>

      {/* Repo list */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
        </div>
      ) : repos.length > 0 ? (
        <div className="space-y-4">
          {repos.map((r) => (
            <div key={r.id} className="flex items-center justify-between rounded-xl border border-border bg-bg-card p-5">
              <div>
                <div className="flex items-center gap-2">
                  <svg className="h-5 w-5 text-white" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
                  </svg>
                  <h3 className="font-semibold">{r.external_id}</h3>
                </div>
                <p className="mt-1 text-xs text-dim">
                  {r.categories?.length || 0} categories
                  {r.last_fetched_at && ` · Last sync: ${new Date(r.last_fetched_at).toLocaleString()}`}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleSync(r.id)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted hover:border-accent hover:text-accent transition-colors"
                >
                  Sync Now
                </button>
                <a
                  href={r.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-lg border border-border px-3 py-1.5 text-xs text-muted hover:border-white hover:text-white transition-colors"
                >
                  Open
                </a>
                <button
                  onClick={() => handleDelete(r.id)}
                  className="rounded-lg border border-border px-3 py-1.5 text-xs text-dim hover:border-red-500/50 hover:text-red-400 transition-colors"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted">
          <p className="mb-2 text-lg">No GitHub repos connected</p>
          <p className="text-sm text-dim">Add a repository above to start extracting knowledge from Discussions.</p>
        </div>
      )}
    </div>
  );
}
