import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: __dirname,
  },
  experimental: {
    serverActions: {
      allowedOrigins: ['behazeld.digisure.in', 'localhost:3000', '127.0.0.1:3000'],
    },
  },
};

export default nextConfig;
