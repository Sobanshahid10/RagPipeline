import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  productionBrowserSourceMaps: false,
  async headers() {
    return [{source:"/:path*",headers:[
      {key:"X-Content-Type-Options",value:"nosniff"},
      {key:"Referrer-Policy",value:"strict-origin-when-cross-origin"},
      {key:"X-Frame-Options",value:"DENY"},
      {key:"Content-Security-Policy",value:"base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'"},
    ]}];
  },
  webpack: (config) => {
    config.resolve.alias.canvas = false;
    config.resolve.alias.encoding = false;
    return config;
  },
  turbopack: {},
};

export default nextConfig;
