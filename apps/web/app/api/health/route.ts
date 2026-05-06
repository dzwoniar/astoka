// Web-side liveness probe. Used by docker-compose healthcheck.
// Does NOT check downstream API — that's the responsibility of /health on the FastAPI side.

export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json({ status: "ok" });
}
