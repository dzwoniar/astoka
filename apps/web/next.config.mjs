/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  experimental: {
    typedRoutes: true,
  },
  async rewrites() {
    // Next.js rewrites run SERVER-SIDE (inside the web container). So "localhost"
    // here means the web container itself, not the api container. Use the internal
    // Docker DNS name `api:8000` when running in compose.
    //
    // Two env vars on purpose:
    //   - INTERNAL_API_URL    → server-side rewrite target (this function)
    //   - NEXT_PUBLIC_API_URL → browser-facing URL, used by `lib/api-client.ts`
    //                          for any direct fetch that bypasses Next rewrites.
    // The browser still hits `/api/*` (relative) by default, so most calls go
    // through these rewrites and never see NEXT_PUBLIC_API_URL.
    const internalApiUrl =
      process.env.INTERNAL_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${internalApiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
