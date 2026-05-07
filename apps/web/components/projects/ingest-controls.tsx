"use client";

import * as React from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { HttpError, ingestApi, uploadFile } from "@/lib/api-client";

interface Props {
  projectId: string;
  onIngested: () => void;
}

export function IngestControls({ projectId, onIngested }: Props) {
  const [mode, setMode] = React.useState<"file" | "youtube">("youtube");
  const [youtubeUrl, setYoutubeUrl] = React.useState("");
  const [file, setFile] = React.useState<File | null>(null);
  const [uploadPct, setUploadPct] = React.useState(0);
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [tosAck, setTosAck] = React.useState(false);

  const submit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "file") {
        if (!file) throw new Error("Wybierz plik");
        await uploadFile(projectId, file, setUploadPct);
      } else {
        if (!youtubeUrl.trim()) throw new Error("Wpisz URL YouTube");
        if (!tosAck) throw new Error("Potwierdź ToS");
        await ingestApi.youtube(projectId, { url: youtubeUrl.trim() });
      }
      onIngested();
      setFile(null);
      setYoutubeUrl("");
      setUploadPct(0);
    } catch (err) {
      if (err instanceof HttpError) setError(err.detail);
      else if (err instanceof Error) setError(err.message);
      else setError("Coś poszło nie tak");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-lg border p-4">
      <div className="mb-4 flex gap-2">
        <Button
          size="sm"
          variant={mode === "youtube" ? "default" : "outline"}
          onClick={() => setMode("youtube")}
        >
          YouTube URL
        </Button>
        <Button
          size="sm"
          variant={mode === "file" ? "default" : "outline"}
          onClick={() => setMode("file")}
        >
          Wgraj plik
        </Button>
      </div>

      {mode === "youtube" ? (
        <div className="space-y-3">
          <div className="space-y-1">
            <Label htmlFor="yt-url">YouTube URL</Label>
            <Input
              id="yt-url"
              type="url"
              placeholder="https://www.youtube.com/watch?v=..."
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
            />
          </div>
          <label className="flex items-start gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={tosAck}
              onChange={(e) => setTosAck(e.target.checked)}
              className="mt-1"
            />
            <span>
              Pobieram wyłącznie własne materiały lub takie, do których mam prawa
              autorskie. Nie używam Astoki do downloadu cudzych treści.
            </span>
          </label>
        </div>
      ) : (
        <div className="space-y-2">
          <Label htmlFor="file">Plik (MP4 / MOV / MKV, max 5 GB)</Label>
          <Input
            id="file"
            type="file"
            accept="video/mp4,video/quicktime,video/x-matroska"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          {file ? (
            <p className="text-xs text-muted-foreground">
              {file.name} — {(file.size / 1024 / 1024).toFixed(1)} MB
            </p>
          ) : null}
          {uploadPct > 0 && uploadPct < 1 ? (
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className="h-full bg-primary transition-all"
                style={{ width: `${uploadPct * 100}%` }}
              />
            </div>
          ) : null}
        </div>
      )}

      {error ? (
        <p className="mt-2 text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      <div className="mt-4">
        <Button
          onClick={() => void submit()}
          disabled={
            submitting ||
            (mode === "youtube" && (!youtubeUrl.trim() || !tosAck)) ||
            (mode === "file" && !file)
          }
        >
          {submitting
            ? "Przetwarzam..."
            : mode === "youtube"
              ? "Pobierz z YouTube"
              : "Wgraj plik"}
        </Button>
      </div>
    </div>
  );
}
