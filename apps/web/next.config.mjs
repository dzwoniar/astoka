/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  experimental: {
    typedRoutes: true,
  },
  async rewrites() {
    // Local dev: proxy /api/* to FastAPI. In production Traefik handles routing.
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
