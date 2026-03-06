/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(self), geolocation=()" },
        ],
      },
    ];
  },
  async redirects() {
    return [
      // Slice 108: Route cleanup — old routes → new routes
      { source: "/mission-control", destination: "/dashboard", permanent: true },
      { source: "/mission-control/analytics", destination: "/content/results", permanent: true },
      { source: "/mission-control/settings", destination: "/brand?tab=settings", permanent: true },
      { source: "/mission-control/orchestrator", destination: "/brand?tab=team", permanent: true },
      { source: "/marketing", destination: "/content", permanent: true },
      { source: "/sales", destination: "/growth", permanent: true },
      { source: "/intelligence", destination: "/jumbo", permanent: true },
      { source: "/studio/agents", destination: "/brand?tab=team", permanent: true },
      { source: "/studio/hooks", destination: "/content/hooks", permanent: true },
    ];
  },
};

module.exports = nextConfig;
