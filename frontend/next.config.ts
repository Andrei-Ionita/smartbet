import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  
  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  
  // Optimize for production on Railway
  poweredByHeader: false,
  compress: true,
  
  // Output standalone for the Railway production image
  output: 'standalone',
  
  // Image optimization
  images: {
    domains: [],
    formats: ['image/webp'],
    unoptimized: true, // Keep image handling predictable in the container
  },
};

export default nextConfig;
