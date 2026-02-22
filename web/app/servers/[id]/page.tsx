import ArticleCard from "@/components/ArticleCard";
import SearchBar from "@/components/SearchBar";
import { getServerArticles } from "@/lib/api";

interface Props {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ page?: string; language?: string; tag?: string }>;
}

export default async function ServerArticlesPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { page: pageStr, language, tag } = await searchParams;
  const serverId = parseInt(id, 10);
  const page = parseInt(pageStr || "1", 10);

  let data;
  try {
    data = await getServerArticles(serverId, page, language, tag);
  } catch {
    data = { items: [], total: 0, page: 1, page_size: 20 };
  }

  const totalPages = Math.ceil(data.total / data.page_size);

  return (
    <div>
      <div className="mb-8">
        <h1 className="mb-2 text-3xl font-bold">Server Knowledge Base</h1>
        <p className="text-muted">
          {data.total} article{data.total !== 1 ? "s" : ""} extracted
          {language && <span> &middot; filtered by <code className="text-accent">{language}</code></span>}
          {tag && <span> &middot; tag <code className="text-accent">{tag}</code></span>}
        </p>
      </div>

      <div className="mb-6 max-w-lg">
        <SearchBar placeholder={`Search in this server...`} />
      </div>

      {data.items.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {data.items.map((article) => (
            <ArticleCard key={article.id} article={article} />
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted">
          No articles found.
        </div>
      )}

      {totalPages > 1 && (
        <div className="mt-8 flex justify-center gap-2">
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <a
              key={p}
              href={`/servers/${id}?page=${p}${language ? `&language=${language}` : ""}${tag ? `&tag=${tag}` : ""}`}
              className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                p === page
                  ? "bg-accent text-white"
                  : "border border-border text-muted hover:border-accent hover:text-white"
              }`}
            >
              {p}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
