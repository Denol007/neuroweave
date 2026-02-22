const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Article {
  id: number;
  symptom: string;
  diagnosis: string;
  solution: string;
  code_snippet: string | null;
  language: string;
  framework: string | null;
  tags: string[];
  confidence: number;
  thread_summary: string;
  quality_score: number;
  is_visible: boolean;
  created_at: string;
  updated_at: string;
}

export interface ArticleBrief {
  id: number;
  thread_summary: string;
  language: string;
  framework: string | null;
  tags: string[];
  confidence: number;
  quality_score: number;
  created_at: string;
}

export interface Server {
  id: number;
  discord_id: string;
  name: string;
  icon_url: string | null;
  member_count: number;
  plan: string;
  created_at: string;
}

export interface SearchResult {
  article: ArticleBrief;
  score: number;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    next: { revalidate: 60 },
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function getServers(): Promise<Server[]> {
  return apiFetch<Server[]>("/api/servers");
}

export async function getServerArticles(
  serverId: number,
  page = 1,
  language?: string,
  tag?: string
): Promise<{ items: ArticleBrief[]; total: number; page: number; page_size: number }> {
  const params = new URLSearchParams({ page: String(page) });
  if (language) params.set("language", language);
  if (tag) params.set("tag", tag);
  return apiFetch(`/api/servers/${serverId}/articles?${params}`);
}

export async function getArticle(id: number): Promise<Article> {
  return apiFetch<Article>(`/api/articles/${id}`);
}

export async function searchArticles(
  query: string,
  server?: number,
  language?: string,
  limit = 20
): Promise<{ results: SearchResult[]; query: string; total: number }> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  if (server) params.set("server", String(server));
  if (language) params.set("language", language);
  return apiFetch(`/api/search?${params}`);
}

// --- Dashboard / Admin APIs (require auth token) ---

export interface ServerStats {
  server_id: number;
  server_name: string;
  total_articles: number;
  total_threads: number;
  total_messages: number;
  noise_filtered: number;
  avg_quality_score: number;
  top_languages: { language: string; count: number }[];
  top_tags: { tag: string; count: number }[];
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export async function getServerStats(serverId: number, token: string): Promise<ServerStats> {
  return apiFetch(`/api/servers/${serverId}/stats`, { headers: authHeaders(token) });
}

export async function setMonitoredChannels(
  serverId: number,
  channelDiscordIds: string[],
  isMonitored: boolean,
  token: string
): Promise<{ updated: number }> {
  return apiFetch(`/api/servers/${serverId}/channels`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ channel_discord_ids: channelDiscordIds, is_monitored: isMonitored }),
  });
}

export async function moderateArticle(
  articleId: number,
  isVisible: boolean,
  token: string
): Promise<{ id: number; is_visible: boolean }> {
  return apiFetch(`/api/articles/${articleId}/moderate?is_visible=${isVisible}`, {
    method: "PATCH",
    headers: authHeaders(token),
  });
}
