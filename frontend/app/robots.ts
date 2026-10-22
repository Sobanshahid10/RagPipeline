import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://rag-pipeline.internal";

  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/chat", "/public-book", "/privacy", "/terms", "/cookies", "/refund"],
        disallow: ["/api/", "/dashboard", "/documents/"],
      },
    ],
    sitemap: `${siteUrl}/sitemap.xml`,
  };
}
