import type {NextConfig} from 'next';
import createNextIntlPlugin from 'next-intl/plugin';
import { buildHstsHeader } from './src/lib/security-headers';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

const hsts = buildHstsHeader(process.env.NODE_ENV === 'production');

const nextConfig: NextConfig = {
  /* config options here */
  // eslint config removed - use .eslintrc.json or eslint.config.js instead
  outputFileTracingRoot: process.cwd(),
  turbopack: {
    root: process.cwd(),
  },
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'placehold.co',
        port: '',
        pathname: '/**',
      },
    ],
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          // Content-Security-Policy is set per request in src/proxy.ts (nonce-based in production;
          // audit M8 / QW8). HSTS is production-only and covers every path, proxied or not.
          ...(hsts ? [{ key: "Strict-Transport-Security", value: hsts }] : []),
        ],
      },
    ];
  },
};

export default withNextIntl(nextConfig);
