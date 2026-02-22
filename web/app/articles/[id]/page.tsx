import CodeBlock from "@/components/CodeBlock";
import TagList from "@/components/TagList";
import { getArticle } from "@/lib/api";
import { notFound } from "next/navigation";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function ArticleDetailPage({ params }: Props) {
  const { id } = await params;

  let article;
  try {
    article = await getArticle(parseInt(id, 10));
  } catch {
    notFound();
  }

  return (
    <article className="mx-auto max-w-3xl">
      {/* Header */}
      <div className="mb-8">
        <div className="mb-3 flex items-center gap-2">
          <span className="rounded-md bg-accent/10 px-2.5 py-1 font-mono text-xs font-medium text-accent-hover">
            {article.language}
          </span>
          {article.framework && (
            <span className="rounded-md bg-white/[0.04] px-2.5 py-1 font-mono text-xs text-muted">
              {article.framework}
            </span>
          )}
          <span className="ml-auto text-sm text-dim">
            {(article.confidence * 100).toFixed(0)}% confidence &middot;
            Quality {(article.quality_score * 100).toFixed(0)}%
          </span>
        </div>
        <h1 className="mb-3 text-3xl font-bold leading-tight">
          {article.thread_summary}
        </h1>
        <TagList tags={article.tags} />
      </div>

      {/* Symptom */}
      <section className="mb-8">
        <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-red-500/10 text-sm text-red-400">!</span>
          Symptom
        </h2>
        <div className="rounded-xl border border-border bg-bg-card p-5 text-[15px] leading-relaxed text-muted">
          {article.symptom}
        </div>
      </section>

      {/* Diagnosis */}
      <section className="mb-8">
        <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-orange-500/10 text-sm text-orange-400">?</span>
          Diagnosis
        </h2>
        <div className="rounded-xl border border-border bg-bg-card p-5 text-[15px] leading-relaxed text-muted">
          {article.diagnosis}
        </div>
      </section>

      {/* Solution */}
      <section className="mb-8">
        <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
          <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-green-500/10 text-sm text-green-400">&#10003;</span>
          Solution
        </h2>
        <div className="rounded-xl border border-border bg-bg-card p-5 text-[15px] leading-relaxed text-muted whitespace-pre-line">
          {article.solution}
        </div>
      </section>

      {/* Code Snippet */}
      {article.code_snippet && (
        <section className="mb-8">
          <h2 className="mb-3 flex items-center gap-2 text-lg font-semibold">
            <span className="inline-flex h-7 w-7 items-center justify-center rounded-lg bg-accent/10 text-sm text-accent-hover">&lt;/&gt;</span>
            Code
          </h2>
          <CodeBlock code={article.code_snippet} language={article.language} />
        </section>
      )}

      {/* Meta */}
      <footer className="border-t border-border pt-6 text-sm text-dim">
        <time>Created: {new Date(article.created_at).toLocaleString()}</time>
      </footer>
    </article>
  );
}
