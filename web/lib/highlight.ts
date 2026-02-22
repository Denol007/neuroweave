import { codeToHtml } from "shiki";

const LANG_MAP: Record<string, string> = {
  javascript: "javascript",
  js: "javascript",
  typescript: "typescript",
  ts: "typescript",
  python: "python",
  py: "python",
  rust: "rust",
  go: "go",
  java: "java",
  cpp: "cpp",
  c: "c",
  ruby: "ruby",
  php: "php",
  swift: "swift",
  kotlin: "kotlin",
  sql: "sql",
  bash: "bash",
  sh: "bash",
  shell: "bash",
  json: "json",
  yaml: "yaml",
  yml: "yaml",
  toml: "toml",
  css: "css",
  html: "html",
  markdown: "markdown",
  md: "markdown",
  dockerfile: "dockerfile",
  docker: "dockerfile",
};

export async function highlight(code: string, language?: string): Promise<string> {
  const lang = LANG_MAP[(language || "").toLowerCase()] || "text";

  try {
    return await codeToHtml(code, {
      lang,
      theme: "github-dark-default",
    });
  } catch {
    // Fallback: return escaped plain text
    const escaped = code
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return `<pre><code>${escaped}</code></pre>`;
  }
}
