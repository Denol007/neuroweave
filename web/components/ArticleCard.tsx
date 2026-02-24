import Link from "next/link";
import type { ArticleBrief } from "@/lib/api";
import TagList from "./TagList";
import SourceBadge from "./SourceBadge";
import ArticleTypeBadge from "./ArticleTypeBadge";

interface ArticleCardProps {
  article: ArticleBrief;
}

export default function ArticleCard({ article }: ArticleCardProps) {
  return (
    <Link
      href={`/articles/${article.id}`}
      className="group block rounded-xl border border-border bg-bg-card p-5 transition-all hover:-translate-y-0.5 hover:border-border-hover hover:shadow-lg hover:shadow-black/20"
    >
      <div className="mb-3 flex items-center gap-2 flex-wrap">
        <SourceBadge source={article.source_type || "discord"} />
        <ArticleTypeBadge type={article.article_type || "troubleshooting"} />
        {article.language && article.language !== "general" && (
          <span className="rounded-md bg-accent/10 px-2 py-0.5 font-mono text-xs font-medium text-accent-hover">
            {article.language}
          </span>
        )}
        {article.framework && (
          <span className="rounded-md bg-white/[0.04] px-2 py-0.5 font-mono text-xs text-muted">
            {article.framework}
          </span>
        )}
        <span className="ml-auto text-xs text-dim">
          {(article.confidence * 100).toFixed(0)}%
        </span>
      </div>

      <h3 className="mb-2 text-[15px] font-semibold leading-snug text-white group-hover:text-accent-hover transition-colors">
        {article.thread_summary}
      </h3>

      <div className="mb-3">
        <TagList tags={article.tags.slice(0, 5)} />
      </div>

      <div className="flex items-center justify-between text-xs text-dim">
        <span>Quality: {(article.quality_score * 100).toFixed(0)}%</span>
        <time>{new Date(article.created_at).toLocaleDateString()}</time>
      </div>
    </Link>
  );
}
