# Web Frontend

Next.js 14 knowledge base portal with server-side rendering and semantic search.

## Stack

- Next.js 14 (App Router)
- TypeScript (strict mode)
- Tailwind CSS
- No additional state management — Server Components + fetch

## API

- Backend: `http://localhost:8000/api` (dev), configurable via `NEXT_PUBLIC_API_URL`
- All data fetching in Server Components (SSR) for SEO
- Client Components only for interactive elements (search input, theme toggle)

## Pages

- `/` — homepage: list of servers with knowledge bases
- `/servers/[id]` — server's articles with tag/language filters
- `/articles/[id]` — full article page: symptom → diagnosis → solution → code snippet
- `/search?q=` — hybrid search (text + semantic) across all servers

## Components

- `ArticleCard` — preview card with tags, language badge, confidence score
- `SearchBar` — search input with debounce
- `CodeBlock` — syntax-highlighted code with copy button
- `TagList` — clickable tag chips for filtering

## Style

- Dark theme by default (matching NeuroWeave brand)
- Minimalist UI, focus on readability
- Code blocks with syntax highlighting (e.g., shiki or prism)
- Responsive: mobile-first design
