"use client";

import { useAuth } from "@/lib/auth-context";
import {
  getServerArticles,
  getServerStats,
  moderateArticle,
  type ArticleBrief,
  type ServerStats,
} from "@/lib/api";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function ServerDashboardPage() {
  const { user, token } = useAuth();
  const router = useRouter();
  const params = useParams();
  const serverId = Number(params.serverId);

  const [stats, setStats] = useState<ServerStats | null>(null);
  const [articles, setArticles] = useState<ArticleBrief[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user || !token) {
      router.push("/login");
      return;
    }
    Promise.all([
      getServerStats(serverId, token).catch(() => null),
      getServerArticles(serverId).catch(() => ({ items: [], total: 0, page: 1, page_size: 20 })),
    ]).then(([s, a]) => {
      setStats(s);
      setArticles(a.items);
      setLoading(false);
    });
  }, [user, token, serverId, router]);

  const handleModerate = async (articleId: number, visible: boolean) => {
    if (!token) return;
    try {
      await moderateArticle(articleId, visible, token);
      setArticles((prev) =>
        prev.map((a) => (a.id === articleId ? { ...a, is_visible: visible } as any : a))
      );
    } catch {}
  };

  if (!user) return null;

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-accent border-t-transparent" />
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={() => router.push("/dashboard")}
          className="mb-2 text-sm text-muted hover:text-white transition-colors"
        >
          &larr; Back to servers
        </button>
        <h1 className="text-3xl font-bold">{stats?.server_name || `Server #${serverId}`}</h1>
      </div>

      {/* Stats Grid */}
      {stats && (
        <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Articles" value={stats.total_articles} color="accent" />
          <StatCard label="Threads" value={stats.total_threads} color="cyan" />
          <StatCard label="Messages" value={stats.total_messages} color="green" />
          <StatCard label="Noise Filtered" value={stats.noise_filtered} color="orange" />
        </div>
      )}

      {/* Quality + Top Languages */}
      {stats && (
        <div className="mb-8 grid gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-border bg-bg-card p-5">
            <h3 className="mb-3 text-sm font-semibold text-muted uppercase tracking-wider">
              Avg Quality Score
            </h3>
            <div className="text-4xl font-bold text-accent-hover">
              {(stats.avg_quality_score * 100).toFixed(0)}%
            </div>
          </div>
          <div className="rounded-xl border border-border bg-bg-card p-5">
            <h3 className="mb-3 text-sm font-semibold text-muted uppercase tracking-wider">
              Top Languages
            </h3>
            <div className="flex flex-wrap gap-2">
              {stats.top_languages.map((l) => (
                <span
                  key={l.language}
                  className="rounded-lg bg-accent/10 px-3 py-1 font-mono text-xs text-accent-hover"
                >
                  {l.language} ({l.count})
                </span>
              ))}
              {stats.top_languages.length === 0 && (
                <span className="text-sm text-dim">No data yet</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Top Tags */}
      {stats && stats.top_tags.length > 0 && (
        <div className="mb-8 rounded-xl border border-border bg-bg-card p-5">
          <h3 className="mb-3 text-sm font-semibold text-muted uppercase tracking-wider">
            Top Tags
          </h3>
          <div className="flex flex-wrap gap-2">
            {stats.top_tags.map((t) => (
              <span
                key={t.tag}
                className="rounded-full border border-border bg-white/[0.03] px-3 py-1 font-mono text-xs text-muted"
              >
                {t.tag} ({t.count})
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Articles with moderation */}
      <div>
        <h2 className="mb-4 text-xl font-semibold">Articles ({articles.length})</h2>
        {articles.length > 0 ? (
          <div className="space-y-3">
            {articles.map((article) => (
              <div
                key={article.id}
                className="flex items-center justify-between rounded-xl border border-border bg-bg-card p-4"
              >
                <div className="min-w-0 flex-1">
                  <a
                    href={`/articles/${article.id}`}
                    className="text-sm font-medium hover:text-accent-hover transition-colors"
                  >
                    {article.thread_summary}
                  </a>
                  <div className="mt-1 flex items-center gap-3 text-xs text-dim">
                    <span className="rounded bg-accent/10 px-1.5 py-0.5 font-mono text-accent-hover">
                      {article.language}
                    </span>
                    <span>Quality: {(article.quality_score * 100).toFixed(0)}%</span>
                    <span>{new Date(article.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <button
                  onClick={() => handleModerate(article.id, false)}
                  className="ml-4 shrink-0 rounded-lg border border-border px-3 py-1.5 text-xs text-dim hover:border-red-500/50 hover:text-red-400 transition-colors"
                >
                  Hide
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-border p-8 text-center text-muted">
            No articles yet. Start monitoring channels to extract knowledge.
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  const colorMap: Record<string, string> = {
    accent: "text-accent-hover",
    cyan: "text-cyan-400",
    green: "text-green-400",
    orange: "text-orange-400",
  };

  return (
    <div className="rounded-xl border border-border bg-bg-card p-5">
      <div className={`text-3xl font-bold ${colorMap[color] || "text-white"}`}>
        {value.toLocaleString()}
      </div>
      <div className="mt-1 text-xs text-muted uppercase tracking-wider">{label}</div>
    </div>
  );
}
