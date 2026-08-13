/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone output is copied into the Railway production image.
  images: {
    domains: ['localhost'],
  },
  output: 'standalone',
  // Baseline browser hardening for every public surface. The CSP intentionally
  // permits Next's inline bootstrap while denying frames, plugins and foreign
  // form submissions. Tighten script-src further only with a nonce migration.
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=()' },
          {
            key: 'Content-Security-Policy',
            value: "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' https://api.betglitch.com; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; upgrade-insecure-requests",
          },
        ],
      },
    ]
  },
}

export default nextConfig
