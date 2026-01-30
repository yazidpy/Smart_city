/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/video_feed',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/video_feed',
        destination: 'http://localhost:8000/video_feed',
      },
    ];
  },
};

export default nextConfig;
