import ArticleCard from "@/components/ArticleCard";
import SearchBar from "@/components/SearchBar";
import { searchArticles } from "@/lib/api";

interface Props {
  searchParams: Promise<{ q?: string; language?: string }>;
}

export default async function SearchPage({ searchParams }: Props) {
  const { q, language } = await searchParams;

  let results: { article: any; score: number }[] = [];
  let total = 0;

  if (q) {
    try {
      const data = await searchArticles(q, undefined, language);
      results = data.results;
      total = data.total;
    } catch {
      // API unavailable
    }
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="mb-4 text-3xl font-bold">Search</h1>
        <div className="max-w-lg">
          <SearchBar defaultValue={q || ""} placeholder="Search knowledge base..." />
        </div>
      </div>

      {q && (
        <p className="mb-6 text-sm text-muted">
          {total} result{total !== 1 ? "s" : ""} for{" "}
          <span className="font-medium text-white">&ldquo;{q}&rdquo;</span>
        </p>
      )}

      {results.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {results.map((result) => (
            <div key={result.article.id} className="relative">
              <ArticleCard article={result.article} />
              <span className="absolute right-3 top-3 rounded bg-accent/10 px-2 py-0.5 font-mono text-xs text-accent-hover">
                {result.score.toFixed(3)}
              </span>
            </div>
          ))}
        </div>
      ) : q ? (
        <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted">
          <p className="mb-2 text-lg">No results found</p>
          <p className="text-sm text-dim">Try different keywords or check your spelling.</p>
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted">
          <p className="text-lg">Enter a search query above</p>
        </div>
      )}
    </div>
  );
}
