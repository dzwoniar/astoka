"use client";

import Link from "next/link";
import * as React from "react";

import { Protected } from "@/components/auth/protected";
import { ProjectCard } from "@/components/projects/project-card";
import { Button } from "@/components/ui/button";
import { projectsApi } from "@/lib/api-client";
import type { ArchiveFilter, ProjectResponse, ProjectSortField } from "@/lib/api-types";
import { useAuth } from "@/lib/auth-context";

function ProjectsList() {
  const { user, logout } = useAuth();
  const [projects, setProjects] = React.useState<ProjectResponse[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [archiveFilter, setArchiveFilter] = React.useState<ArchiveFilter>("active");
  const [sortBy, setSortBy] = React.useState<ProjectSortField>("updated_at");

  React.useEffect(() => {
    let active = true;
    projectsApi
      .list({
        archive_filter: archiveFilter,
        sort_by: sortBy,
        sort_desc: true,
      })
      .then((res) => {
        if (active) setProjects(res.items);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : "Failed to load");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [archiveFilter, sortBy]);

  return (
    <main className="container py-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Projekty</h1>
          <p className="text-sm text-muted-foreground">Zalogowany jako: {user?.username}</p>
        </div>
        <div className="flex gap-2">
          <Link href="/projects/new">
            <Button>Nowy projekt</Button>
          </Link>
          <Button variant="outline" onClick={() => void logout()}>
            Wyloguj
          </Button>
        </div>
      </header>

      <div className="mb-4 flex flex-wrap gap-2">
        <select
          value={archiveFilter}
          onChange={(e) => {
            setLoading(true);
            setError(null);
            setArchiveFilter(e.target.value as ArchiveFilter);
          }}
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
        >
          <option value="active">Aktywne</option>
          <option value="archived">Zarchiwizowane</option>
          <option value="all">Wszystkie</option>
        </select>
        <select
          value={sortBy}
          onChange={(e) => {
            setLoading(true);
            setError(null);
            setSortBy(e.target.value as ProjectSortField);
          }}
          className="rounded-md border border-input bg-background px-3 py-1.5 text-sm"
        >
          <option value="updated_at">Sortuj: ostatnia modyfikacja</option>
          <option value="created_at">Sortuj: utworzenie</option>
          <option value="name">Sortuj: nazwa</option>
          <option value="client">Sortuj: klient</option>
        </select>
      </div>

      {error ? (
        <div className="mb-4 rounded-md border border-destructive bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      ) : null}

      {loading ? (
        <div className="text-center text-muted-foreground">Ładowanie projektów...</div>
      ) : projects.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <p className="mb-4 text-muted-foreground">
            Brak projektów. Utwórz pierwszy żeby rozpocząć.
          </p>
          <Link href="/projects/new">
            <Button>Nowy projekt</Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((p) => (
            <ProjectCard key={p.id} project={p} />
          ))}
        </div>
      )}
    </main>
  );
}

export default function HomePage() {
  return (
    <Protected>
      <ProjectsList />
    </Protected>
  );
}
