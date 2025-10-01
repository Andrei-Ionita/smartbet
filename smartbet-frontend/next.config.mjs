/** @type {import('next').NextConfig} */
const nextConfig = {
  // Prevent chunk loading errors during development
  swcMinify: false,
  experimental: {
    esmExternals: 'loose'
  },
  // Add webpack configuration to prevent chunk errors
  webpack: (config, { dev, isServer }) => {
    if (dev) {
      // Disable chunk splitting in development
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            default: false,
            vendors: false,
          },
        },
      };
    }
    return config;
  },
  // Disable static optimization to prevent chunk issues
  output: 'standalone'
};

export default nextConfig; 