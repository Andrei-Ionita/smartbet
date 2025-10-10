/** @type {import('next').NextConfig} */
const nextConfig = {
  // Optimized for Vercel deployment
  experimental: {
    appDir: true,
  },
  images: {
    domains: ['localhost'],
  },
  // API routes configuration
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET, POST, PUT, DELETE, OPTIONS' },
          { key: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' },
        ],
      },
    ];
  },
};

export default nextConfig; 