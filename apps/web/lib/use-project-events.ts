"use client";

import * as React from "react";

import type { JobUpdateEvent } from "./api-types";

type ProjectEventHandler = (event: JobUpdateEvent) => void;

/** Subscribe to /projects/{id}/events SSE stream. Calls handler on every event. */
export function useProjectEvents(
  projectId: string | null | undefined,
  onEvent: ProjectEventHandler,
): { connected: boolean } {
  const [connected, setConnected] = React.useState(false);
  const handlerRef = React.useRef(onEvent);
  handlerRef.current = onEvent;

  React.useEffect(() => {
    if (!projectId) return;

    const url = `/api/projects/${projectId}/events`;
    const source = new EventSource(url, { withCredentials: true });

    source.addEventListener("open", () => setConnected(true));
    source.addEventListener("error", () => setConnected(false));

    const onMessage = (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data) as JobUpdateEvent;
        handlerRef.current(data);
      } catch {
        // Ignore malformed payloads.
      }
    };
    source.addEventListener("job_update", onMessage as EventListener);
    source.addEventListener("source_material_ready", onMessage as EventListener);
    source.addEventListener("highlights_ready", onMessage as EventListener);

    return () => {
      source.close();
    };
  }, [projectId]);

  return { connected };
}
