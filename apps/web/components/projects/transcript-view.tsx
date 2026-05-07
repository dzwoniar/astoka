"use client";

import * as React from "react";

import { transcriptsApi } from "@/lib/api-client";
import type { TranscriptResponse } from "@/lib/api-types";

export function TranscriptView({ sourceMaterialId }: { sourceMaterialId: string }) {
  const [transcript, setTranscript] = React.useState<TranscriptResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let mounted = true;
    transcriptsApi
      .get(sourceMaterialId)
      .then((t) => {
        if (mounted) setTranscript(t);
      })
      .catch((err) => {
        if (mounted) setError((err as Error)?.message ?? "Brak transkrypcji");
      });
    return () => {
      mounted = false;
    };
  }, [sourceMaterialId]);

  if (error) {
    return <p className="text-sm text-muted-foreground">{error}</p>;
  }

  if (!transcript) {
    return <p className="text-sm text-muted-foreground">Ładuję transkrypcję...</p>;
  }

  return (
    <div className="space-y-3">
      <div className="text-xs text-muted-foreground">
        Język: <code>{transcript.language}</code> · Model:{" "}
        <code>{transcript.model_id}</code>
        {transcript.avg_confidence != null
          ? ` · avg_confidence ${(transcript.avg_confidence * 100).toFixed(0)}%`
          : null}
      </div>
      <div className="max-h-96 overflow-y-auto rounded-md border bg-card p-3 text-sm leading-relaxed">
        {transcript.segments_json.map((seg, idx) => (
          <span key={idx}>
            <span className="text-xs text-muted-foreground">
              [{seg.start.toFixed(1)}s]{" "}
            </span>
            <span>{seg.text}</span>{" "}
          </span>
        ))}
      </div>
    </div>
  );
}
