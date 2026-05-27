import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "BeHazel'd",
    short_name: "BeHazel'd",
    description:
      "Luxury Indian couture, handcrafted atelier collections, and occasionwear handpicked from the largest Chikankari market in the world.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#120A05",
    theme_color: "#120A05",
    orientation: "portrait",
    icons: [
      {
        src: "/Logo.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/Logo2.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/Logo2.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
