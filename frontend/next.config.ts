import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  turbopack: { root: process.env.NEWS_BUILD_ROOT || process.cwd() },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.NEWS_API_INTERNAL_URL || "http://localhost:8001"}/api/:path*` }]
  },
}

export default nextConfig
