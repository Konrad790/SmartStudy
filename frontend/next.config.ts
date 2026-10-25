import type { NextConfig } from "next";

const apiTarget =
  process.env.API_URL?.trim() ||
  process.env.NEXT_PUBLIC_API_URL?.trim() ||
  "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return {
      beforeFiles: [{ source: "/backend-api/:path*", destination: `${apiTarget}/:path*` }],
    };
  },
};

export default nextConfig;
