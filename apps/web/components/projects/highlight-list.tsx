"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { highlightsApi, HttpError } from "@/lib/api-client";
import type { HighlightResponse } from "@/lib/api-types";

interface Props {
  projectId: string;
  refreshKey: number;
}

const TYPOLOGY_COLOR: Record<string, string> = {
  opinion_bomb: "bg-pink-500/20 text-pink-300",
  hook_moment: "bg-orange-500/20 text-orange-300",
  story_peak: "bg-purple-500/20 text-purple-300",
  practical_value: "bg-emerald-500/20 text-emerald-300",
  revelation: "bg-blue-500/20 text-blue-300",
  comedy_punch: "bg-yellow-500/20 text-yellow-300",
};

function fmtTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

export function HighlightList({ projectId, refreshKey }: Props) {
  const [highlights, setHighlights] = React.useState<HighlightResponse[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState<string | null>(null);

  const load = React.useCallback(() => {
    setLoading(true);
    highlightsApi
      .list(projectId, false)
      .then(setHighlights)
      .catch((err) => setError(err instanceof HttpError ? err.detail : "Failed"))
      .finally(() => setLoading(false));
  }, [projectId]);

  React.useEffect(() => {
    load();
  }, [load, refreshKey]);

  const update = async (
    id: string,
    fn: (id: string) => Promise<HighlightResponse>,
  ) => {
    setBusy(id);
    try {
      await fn(id);
      load();
    } finally {
      setBusy(null);
    }
  };

  if (loading) {
    return <p className="text-sm text-muted-foreground">Ładuję highlights...</p>;
  }
  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }
  if (highlights.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Brak propozycji. Highlights pojawią się po zakończeniu transkrypcji + analizy.
      </p>
    );
  }

  const pending = highlights.filter((h) => h.status === "pending");
  const accepted = highlights.filter((h) => h.status === "accepted");

  return (
    <div className="space-y-6">
      {pending.length > 0 ? (
        <div>
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
            Propozycje ({pending.length})
          </h3>
          <ul className="space-y-3">
            {pending.map((h) => (
              <HighlightCard
                key={h.id}
                highlight={h}
                onAccept={() => update(h.id, highlightsApi.accept)}
                onReject={() => update(h.id, highlightsApi.reject)}
                onHide={() => update(h.id, highlightsApi.hide)}
                busy={busy === h.id}
              />
            ))}
          </ul>
        </div>
      ) : null}

      {accepted.length > 0 ? (
        <div>
          <h3 className="mb-3 text-sm font-semibold text-muted-foreground">
            Zaakceptowane ({accepted.length})
          </h3>
          <ul className="space-y-3">
            {accepted.map((h) => (
              <HighlightCard
                key={h.id}
                highlight={h}
                onReject={() => update(h.id, highlightsApi.reject)}
                busy={busy === h.id}
              />
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function HighlightCard({
  highlight,
  onAccept,
  onReject,
  onHide,
  busy,
}: {
  highlight: HighlightResponse;
  onAccept?: () => void;
  onReject?: () => void;
  onHide?: () => void;
  busy: boolean;
}) {
  const typoColor =
    highlight.typology && TYPOLOGY_COLOR[highlight.typology]
      ? TYPOLOGY_COLOR[highlight.typology]
      : "bg-muted text-muted-foreground";

  return (
    <li className="rounded-lg border p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">
              {fmtTime(highlight.start_s)} – {fmtTime(highlight.end_s)} (
              {(highlight.end_s - highlight.start_s).toFixed(1)}s)
            </span>
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-semibold">
              score {highlight.viral_score}
            </span>
            {highlight.typology ? (
              <span className={`rounded-full px-2 py-0.5 text-xs ${typoColor}`}>
                {highlight.typology}
              </span>
            ) : null}
            {highlight.audio_corrected ? (
              <span className="rounded-full bg-green-500/20 px-2 py-0.5 text-xs text-green-300">
                audio-corrected
              </span>
            ) : null}
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
              {highlight.llm_provider}
            </span>
          </div>

          {highlight.suggested_title ? (
            <h4 className="mt-2 font-semibold">{highlight.suggested_title}</h4>
          ) : null}

          {highlight.hook_sentence ? (
            <blockquote className="mt-2 border-l-2 pl-3 text-sm italic">
              &ldquo;{highlight.hook_sentence}&rdquo;
            </blockquote>
          ) : null}

          {highlight.virality_reason ? (
            <p className="mt-2 text-xs text-muted-foreground">
              {highlight.virality_reason}
            </p>
          ) : null}

          {highlight.confidence != null ? (
            <p className="mt-1 text-xs text-muted-foreground">
              confidence: {(highlight.confidence * 100).toFixed(0)}%
              {highlight.confidence < 0.6 ? " (sprawdź ręcznie)" : ""}
            </p>
          ) : null}
        </div>
      </div>

      <div className="mt-3 flex gap-2">
        {onAccept ? (
          <Button size="sm" onClick={onAccept} disabled={busy}>
            Akceptuj
          </Button>
        ) : null}
        {onReject ? (
          <Button size="sm" variant="outline" onClick={onReject} disabled={busy}>
            Odrzuć
          </Button>
        ) : null}
        {onHide ? (
          <Button size="sm" variant="ghost" onClick={onHide} disabled={busy}>
            Schowaj
          </Button>
        ) : null}
      </div>
    </li>
  );
}
