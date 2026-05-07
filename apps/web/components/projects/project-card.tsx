"use client";

import Link from "next/link";

import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { ProjectResponse } from "@/lib/api-types";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString("pl-PL", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ProjectCard({ project }: { project: ProjectResponse }) {
  return (
    <Link href={`/projects/${project.id}`} className="block">
      <Card className="transition-colors hover:bg-accent">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="space-y-1">
              <h3 className="text-lg font-semibold leading-tight">{project.name}</h3>
              {project.client ? (
                <p className="text-sm text-muted-foreground">{project.client}</p>
              ) : null}
            </div>
            {project.is_archived ? (
              <span className="rounded-full bg-muted px-2 py-1 text-xs">archived</span>
            ) : null}
          </div>
        </CardHeader>
        <CardContent className="text-xs text-muted-foreground">
          <div className="flex items-center gap-4">
            <span>{project.source_materials_count} materiał(ów)</span>
            <span>{project.clips_count} klip(ów)</span>
          </div>
          <div className="mt-1">
            Modyfikowano: {formatDate(project.updated_at)}
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
