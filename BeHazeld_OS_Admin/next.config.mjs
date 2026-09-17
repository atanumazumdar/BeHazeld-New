/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: '10mb',
      allowedOrigins: ['admin.behazeld.digisure.in', 'localhost:3001', '127.0.0.1:3001'],
    },
  },
};

export default nextConfig;
