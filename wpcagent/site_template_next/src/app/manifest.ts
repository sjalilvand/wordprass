import type { MetadataRoute } from "next";
import { getSettings } from "@/lib/settings";

/** مانیفست PWA — امکان نصب سامانه به‌عنوان اپ موبایل (نام سایت از تنظیمات) */
export default async function manifest(): Promise<MetadataRoute.Manifest> {
  let name = "سامانه پویا";
  let short = "سامانه";
  let description = "سامانه رسمی: اخبار، اطلاعیه‌ها، گالری، فرم‌ها و دستیار هوشمند";
  try {
    const s = await getSettings();
    if (s.siteName) name = s.siteName;
    if (s.siteShort) short = s.siteShort;
    if (s.tagline) description = s.tagline;
  } catch {
    // دیتابیس هنوز آماده نیست
  }
  return {
    name,
    short_name: short,
    description,
    lang: "fa",
    dir: "rtl",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#faf8f2",
    theme_color: "#0b5d51",
    categories: ["education", "news"],
    icons: [
      {
        src: "/icons/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icons/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
    shortcuts: [
      {
        name: "اخبار",
        url: "/news",
        icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }],
      },
      {
        name: "اطلاعیه‌ها",
        url: "/announcements",
        icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }],
      },
      {
        name: "تماس با ما",
        url: "/contact",
        icons: [{ src: "/icons/icon-192.png", sizes: "192x192" }],
      },
    ],
  };
}
