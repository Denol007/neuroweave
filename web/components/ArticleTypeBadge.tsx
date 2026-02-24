interface ArticleTypeBadgeProps {
  type: string;
}

const config: Record<string, { label: string; bg: string; text: string }> = {
  troubleshooting: { label: "Bug Fix", bg: "bg-red-500/10", text: "text-red-400" },
  question_answer: { label: "Q&A", bg: "bg-blue-500/10", text: "text-blue-400" },
  guide: { label: "Guide", bg: "bg-green-500/10", text: "text-green-400" },
  discussion_summary: { label: "Discussion", bg: "bg-yellow-500/10", text: "text-yellow-400" },
};

export default function ArticleTypeBadge({ type }: ArticleTypeBadgeProps) {
  const c = config[type] || config.troubleshooting;
  return (
    <span className={`rounded-md px-2 py-0.5 text-xs font-medium ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  );
}
