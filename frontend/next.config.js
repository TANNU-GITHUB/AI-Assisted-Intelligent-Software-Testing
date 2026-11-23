/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,
  },
  images: { unoptimized: true },
  // Large files/repos can take several minutes while NVIDIA falls back to Ollama.
  experimental: {
    proxyTimeout: 10 * 60 * 1000,
  },
  async rewrites() {
    const backend = process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backend}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
