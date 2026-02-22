import Link from "next/link";

interface TagListProps {
  tags: string[];
  serverId?: number;
  clickable?: boolean;
}

export default function TagList({ tags, serverId, clickable = false }: TagListProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {tags.map((tag) =>
        clickable && serverId ? (
          <Link
            key={tag}
            href={`/servers/${serverId}?tag=${tag}`}
            className="rounded-full border border-border bg-white/[0.03] px-2.5 py-0.5 font-mono text-xs text-muted transition-colors hover:border-accent hover:text-accent-hover"
          >
            {tag}
          </Link>
        ) : (
          <span
            key={tag}
            className="rounded-full border border-border bg-white/[0.03] px-2.5 py-0.5 font-mono text-xs text-muted"
          >
            {tag}
          </span>
        )
      )}
    </div>
  );
}
