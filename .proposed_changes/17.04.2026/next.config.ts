import type {NextConfig} from 'next';

const nextConfig: NextConfig = {
  /* config options here */
  // eslint config removed - use .eslintrc.json or eslint.config.js instead
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
};

export default nextConfig;
