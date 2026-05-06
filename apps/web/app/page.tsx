import Link from "next/link";

export default function HomePage() {
  return (
    <main className="container flex min-h-screen flex-col items-center justify-center gap-6">
      <h1 className="text-4xl font-bold tracking-tight">Astoka</h1>
      <p className="max-w-md text-center text-muted-foreground">
        Wewnętrzne narzędzie Akademii 100k do automatycznej produkcji shortów.
      </p>
      <div className="flex gap-3 text-sm">
        <Link
          href="/api/health"
          className="rounded-md border border-border px-4 py-2 hover:bg-accent"
        >
          API health
        </Link>
        <span className="rounded-md border border-border px-4 py-2 text-muted-foreground">
          Sprint 0 — setup
        </span>
      </div>
    </main>
  );
}
