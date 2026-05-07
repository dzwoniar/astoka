"use client";

import { useRouter } from "next/navigation";
import * as React from "react";

import { Protected } from "@/components/auth/protected";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { projectsApi, HttpError } from "@/lib/api-client";

function NewProjectForm() {
  const router = useRouter();
  const [name, setName] = React.useState("");
  const [client, setClient] = React.useState("");
  const [error, setError] = React.useState<string | null>(null);
  const [submitting, setSubmitting] = React.useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const project = await projectsApi.create({
        name: name.trim(),
        client: client.trim() || null,
      });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof HttpError ? err.detail : "Failed to create project");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="container max-w-2xl py-8">
      <Card>
        <CardHeader>
          <CardTitle>Nowy projekt</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={onSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Nazwa projektu *</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="np. Webinar Klient X — Maj 2026"
                required
                maxLength={255}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="client">Klient (opcjonalnie)</Label>
              <Input
                id="client"
                value={client}
                onChange={(e) => setClient(e.target.value)}
                placeholder="np. Akademia 100k"
                maxLength={100}
              />
            </div>
            {error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
            <div className="flex gap-2">
              <Button type="submit" disabled={submitting || !name.trim()}>
                {submitting ? "Tworzę..." : "Utwórz projekt"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.back()}
              >
                Anuluj
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}

export default function NewProjectPage() {
  return (
    <Protected>
      <NewProjectForm />
    </Protected>
  );
}
