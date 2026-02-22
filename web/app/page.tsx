import Link from "next/link";
import SearchBar from "@/components/SearchBar";
import { getServers, type Server } from "@/lib/api";

async function loadServers(): Promise<Server[]> {
  try {
    return await getServers();
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const servers = await loadServers();

  return (
    <div>
      <section className="mb-12 text-center">
        <h1 className="mb-4 text-5xl font-extrabold tracking-tight">
          <span className="bg-gradient-to-r from-accent to-cyan-400 bg-clip-text text-transparent">
            NeuroWeave
          </span>
        </h1>
        <p className="mx-auto mb-8 max-w-xl text-lg text-muted">
          Structured technical knowledge extracted from Discord communities.
          Search solutions, code snippets, and debugging guides.
        </p>
        <div className="mx-auto max-w-lg">
          <SearchBar placeholder="Search across all servers..." />
        </div>
      </section>

      <section>
        <h2 className="mb-6 text-xl font-semibold">Servers</h2>
        {servers.length > 0 ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {servers.map((server) => (
              <Link
                key={server.id}
                href={`/servers/${server.id}`}
                className="group rounded-xl border border-border bg-bg-card p-5 transition-all hover:-translate-y-0.5 hover:border-border-hover hover:shadow-lg hover:shadow-black/20"
              >
                <div className="mb-3 flex items-center gap-3">
                  {server.icon_url ? (
                    <img
                      src={server.icon_url}
                      alt=""
                      className="h-10 w-10 rounded-full"
                    />
                  ) : (
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/20 text-sm font-bold text-accent">
                      {server.name.charAt(0)}
                    </div>
                  )}
                  <div>
                    <h3 className="font-semibold group-hover:text-accent-hover transition-colors">
                      {server.name}
                    </h3>
                    <p className="text-xs text-dim">
                      {server.member_count.toLocaleString()} members
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs text-dim">
                  <span className="rounded bg-white/[0.04] px-2 py-0.5 font-mono">
                    {server.plan}
                  </span>
                  <span>
                    Joined {new Date(server.created_at).toLocaleDateString()}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-border p-12 text-center text-muted">
            <p className="mb-2 text-lg">No servers yet</p>
            <p className="text-sm text-dim">
              Add the NeuroWeave bot to your Discord server to get started.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
