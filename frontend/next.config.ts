import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  
  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  
  // Optimize for production on Render
  poweredByHeader: false,
  compress: true,
  
  // Output standalone for better performance on Render
  output: 'standalone',
  
  // Image optimization
  images: {
    domains: [],
    formats: ['image/webp'],
    unoptimized: true, // Disable image optimization for Render compatibility
  },
};

export default nextConfig;
