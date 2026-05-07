"use client";

import type { JobResponse, SourceMaterialResponse } from "@/lib/api-types";

interface Props {
  sourceMaterials: SourceMaterialResponse[];
  jobs: JobResponse[];
}

const STATUS_LABEL: Record<JobResponse["status"], string> = {
  pending: "oczekuje",
  running: "w toku",
  succeeded: "gotowe",
  failed: "błąd",
  cancelled: "anulowane",
};

const STATUS_COLOR: Record<JobResponse["status"], string> = {
  pending: "bg-muted text-muted-foreground",
  running: "bg-blue-500/20 text-blue-300",
  succeeded: "bg-green-500/20 text-green-300",
  failed: "bg-destructive/20 text-destructive",
  cancelled: "bg-muted text-muted-foreground",
};

export function SourceMaterialList({ sourceMaterials, jobs }: Props) {
  if (sourceMaterials.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Brak materiałów. Wgraj plik lub wklej URL YouTube wyżej.
      </p>
    );
  }

  return (
    <ul className="space-y-3">
      {sourceMaterials.map((sm) => {
        const smJobs = jobs
          .filter((j) => j.source_material_id === sm.id)
          .sort((a, b) => a.created_at.localeCompare(b.created_at));
        const latestJob = smJobs[smJobs.length - 1];

        return (
          <li
            key={sm.id}
            className="rounded-md border p-3"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium">
                  {sm.original_filename ?? sm.youtube_url ?? sm.id}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  <span className="rounded bg-muted px-1.5 py-0.5">
                    {sm.source_type}
                  </span>
                  {sm.duration_s != null ? (
                    <span>długość: {sm.duration_s.toFixed(1)}s</span>
                  ) : null}
                  {sm.width != null && sm.height != null ? (
                    <span>
                      {sm.width}×{sm.height}
                      {sm.fps != null ? ` @ ${sm.fps.toFixed(0)}fps` : ""}
                    </span>
                  ) : null}
                  {sm.detected_language ? (
                    <span>język: {sm.detected_language}</span>
                  ) : null}
                </div>
              </div>
            </div>

            {smJobs.length > 0 ? (
              <div className="mt-3 space-y-2">
                {smJobs.map((job) => (
                  <div key={job.id}>
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-mono">{job.job_type}</span>
                        <span
                          className={`rounded px-1.5 py-0.5 ${STATUS_COLOR[job.status]}`}
                        >
                          {STATUS_LABEL[job.status]}
                        </span>
                      </div>
                      {job.status === "running" ? (
                        <span className="font-mono text-muted-foreground">
                          {Math.round(job.progress * 100)}%
                        </span>
                      ) : null}
                    </div>
                    {job.status === "running" ? (
                      <div className="mt-1 h-1 overflow-hidden rounded-full bg-muted">
                        <div
                          className="h-full bg-blue-500 transition-all"
                          style={{ width: `${Math.round(job.progress * 100)}%` }}
                        />
                      </div>
                    ) : null}
                    {job.progress_message ? (
                      <p className="mt-1 text-xs text-muted-foreground">
                        {job.progress_message}
                      </p>
                    ) : null}
                    {job.error_message ? (
                      <p className="mt-1 text-xs text-destructive">
                        Błąd: {job.error_message}
                      </p>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-2 text-xs text-muted-foreground">
                {latestJob ? `Status: ${latestJob.status}` : "Brak zadań"}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
