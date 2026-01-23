import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  reactStrictMode: true,
  // Exclude native modules from Webpack bundling - they run on the server only
  serverExternalPackages: ['@databricks/sql', 'lz4'],
};

export default nextConfig;
