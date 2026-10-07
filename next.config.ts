import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Contentstack asset/image delivery hosts (all regions)
    remotePatterns: [
      { protocol: "https", hostname: "*-assets.contentstack.com" },
      { protocol: "https", hostname: "assets.contentstack.io" },
      { protocol: "https", hostname: "*-images.contentstack.com" },
      { protocol: "https", hostname: "images.contentstack.io" },
      // BigCommerce product images
      { protocol: "https", hostname: "cdn11.bigcommerce.com" },
    ],
  },
};

export default nextConfig;
