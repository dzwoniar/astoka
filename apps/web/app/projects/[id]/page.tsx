"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { Protected } from "@/components/auth/protected";
import { HighlightList } from "@/components/projects/highlight-list";
import { IngestControls } from "@/components/projects/ingest-controls";
import { SourceMaterialList } from "@/components/projects/source-material-list";
import { TranscriptView } from "@/components/projects/transcript-view";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { HttpError, ingestApi, projectsApi } from "@/lib/api-client";
import type {
  JobResponse,
  ProjectResponse,
  SourceMaterialResponse,
} from "@/lib/api-types";
import { useProjectEvents } from "@/lib/use-project-events";

function ProjectDetail() {
  const params = useParams<{ id: string }>();
  const id = params?.id;

  const [project, setProject] = React.useState<ProjectResponse | null>(null);
  const [sourceMaterials, setSourceMaterials] = React.useState<SourceMaterialResponse[]>(
    [],
  );
  const [jobs, setJobs] = React.useState<JobResponse[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [archiving, setArchiving] = React.useState(false);

  const refresh = React.useCallback(async () => {
    if (!id) return;
    try {
      const [p, sms, js] = await Promise.all([
        projectsApi.get(id),
        ingestApi.listSourceMaterials(id),
        ingestApi.listJobs(id),
      ]);
      setProject(p);
      setSourceMaterials(sms);
      setJobs(js);
    } catch (err) {
      setError(err instanceof HttpError ? err.detail : "Failed to load project");
    } finally {
      setLoading(false);
    }
  }, [id]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const { connected } = useProjectEvents(id, (ev) => {
    setJobs((prev) => {
      // Update existing or insert new.
      const idx = prev.findIndex((j) => j.id === ev.job_id);
      const updatedJob: JobResponse = {
        id: ev.job_id,
        source_material_id: ev.source_material_id,
        job_type: ev.job_type,
        status: ev.status,
        progress: ev.progress,
        progress_message: ev.progress_message,
        started_at: idx >= 0 ? prev[idx].started_at : null,
        finished_at:
          ev.status === "succeeded" || ev.status === "failed"
            ? new Date().toISOString()
            : idx >= 0
              ? prev[idx].finished_at
              : null,
        error_message: ev.error_message,
        result: idx >= 0 ? prev[idx].result : {},
        created_at: idx >= 0 ? prev[idx].created_at : new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = updatedJob;
        return next;
      }
      return [...prev, updatedJob];
    });
    // Refresh source_material list when a job completes (metadata may have changed).
    if (ev.status === "succeeded" || ev.status === "failed") {
      void ingestApi
        .listSourceMaterials(id ?? "")
        .then(setSourceMaterials)
        .catch(() => undefined);
    }
  });

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
      <main className="container py-8 text-center text-muted-foreground">
        Ładowanie...
      </main>
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
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            {project.is_archived ? (
              <span className="rounded-full bg-muted px-2 py-1">archived</span>
            ) : null}
            <span
              className={`rounded-full px-2 py-1 ${
                connected
                  ? "bg-green-500/20 text-green-300"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              SSE: {connected ? "online" : "offline"}
            </span>
          </div>
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

      {!project.is_archived ? (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Dodaj materiał</CardTitle>
          </CardHeader>
          <CardContent>
            <IngestControls projectId={project.id} onIngested={refresh} />
          </CardContent>
        </Card>
      ) : null}

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">
            Materiały źródłowe ({sourceMaterials.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <SourceMaterialList sourceMaterials={sourceMaterials} jobs={jobs} />
        </CardContent>
      </Card>

      {sourceMaterials.length > 0 ? (
        <>
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="text-lg">Transkrypcja</CardTitle>
            </CardHeader>
            <CardContent>
              <TranscriptView sourceMaterialId={sourceMaterials[0].id} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Highlights</CardTitle>
            </CardHeader>
            <CardContent>
              <HighlightList projectId={project.id} refreshKey={jobs.length} />
            </CardContent>
          </Card>
        </>
      ) : null}
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
