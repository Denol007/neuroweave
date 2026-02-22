import { highlight } from "@/lib/highlight";
import CopyButton from "./CopyButton";

interface CodeBlockProps {
  code: string;
  language?: string;
}

export default async function CodeBlock({ code, language }: CodeBlockProps) {
  const html = await highlight(code, language);

  return (
    <div className="group relative rounded-xl border border-border overflow-hidden">
      <div className="flex items-center justify-between border-b border-border bg-white/[0.02] px-4 py-2">
        <span className="font-mono text-xs text-muted">{language || "code"}</span>
        <CopyButton text={code} />
      </div>
      <div
        className="overflow-x-auto [&_pre]:!m-0 [&_pre]:!rounded-none [&_pre]:!border-0 [&_pre]:!p-4 [&_pre]:!bg-[#0d0d10] [&_code]:!font-mono [&_code]:!text-sm [&_code]:!leading-relaxed"
        dangerouslySetInnerHTML={{ __html: html }}
      />
    </div>
  );
}
