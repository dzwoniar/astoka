"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import * as React from "react";

import { Protected } from "@/components/auth/protected";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { projectsApi, HttpError } from "@/lib/api-client";
import type { ProjectResponse } from "@/lib/api-types";

function ProjectDetail() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = React.useState<ProjectResponse | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [archiving, setArchiving] = React.useState(false);

  const id = params?.id;

  React.useEffect(() => {
    if (!id) return;
    setLoading(true);
    projectsApi
      .get(id)
      .then(setProject)
      .catch((err) => {
        setError(err instanceof HttpError ? err.detail : "Failed to load project");
      })
      .finally(() => setLoading(false));
  }, [id]);

  const archive = async () => {
    if (!project) return;
    setArchiving(true);
    try {
      const updated = await projectsApi.archive(project.id);
      setProject(updated);
    } catch (err) {
      setError(err instanceof HttpError ? err.detail : "Failed to archive");
    } finally {
      setArchiving(false);
    }
  };

  const restore = async () => {
    if (!project) return;
    setArchiving(true);
    try {
      const updated = await projectsApi.restore(project.id);
      setProject(updated);
    } catch (err) {
      setError(err instanceof HttpError ? err.detail : "Failed to restore");
    } finally {
      setArchiving(false);
    }
  };

  if (loading) {
    return (
      <main className="container py-8 text-center text-muted-foreground">Ładowanie...</main>
    );
  }
  if (error || !project) {
    return (
      <main className="container py-8">
        <p className="text-destructive">{error ?? "Nie znaleziono projektu"}</p>
        <Link href="/" className="mt-4 inline-block">
          <Button variant="outline">← Wróć do listy</Button>
        </Link>
      </main>
    );
  }

  return (
    <main className="container py-8">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <Link href="/" className="text-sm text-muted-foreground hover:underline">
            ← Wszystkie projekty
          </Link>
          <h1 className="mt-2 text-3xl font-bold">{project.name}</h1>
          {project.client ? (
            <p className="text-sm text-muted-foreground">Klient: {project.client}</p>
          ) : null}
          {project.is_archived ? (
            <span className="mt-2 inline-block rounded-full bg-muted px-2 py-1 text-xs">
              archived
            </span>
          ) : null}
        </div>
        <div className="flex gap-2">
          {project.is_archived ? (
            <Button onClick={() => void restore()} disabled={archiving}>
              Przywróć
            </Button>
          ) : (
            <Button variant="outline" onClick={() => void archive()} disabled={archiving}>
              Archiwizuj
            </Button>
          )}
        </div>
      </header>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Materiały źródłowe</CardTitle>
          </CardHeader>
          <CardContent>
            {project.source_materials_count === 0 ? (
              <p className="text-sm text-muted-foreground">
                Brak materiałów. Wgrywanie i pipeline pojawi się w Phase B (ingest) tego sprintu.
              </p>
            ) : (
              <p>{project.source_materials_count} materiał(ów)</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Wygenerowane klipy</CardTitle>
          </CardHeader>
          <CardContent>
            {project.clips_count === 0 ? (
              <p className="text-sm text-muted-foreground">
                Brak klipów. Pojawią się po wgraniu materiału + analizie.
              </p>
            ) : (
              <p>{project.clips_count} klip(ów)</p>
            )}
          </CardContent>
        </Card>
      </div>

      <details className="mt-8">
        <summary className="cursor-pointer text-sm text-muted-foreground">Surowe dane</summary>
        <pre className="mt-2 overflow-auto rounded-md border bg-muted p-3 text-xs">
          {JSON.stringify(project, null, 2)}
        </pre>
      </details>
    </main>
  );
}

export default function ProjectDetailPage() {
  return (
    <Protected>
      <ProjectDetail />
    </Protected>
  );
}
