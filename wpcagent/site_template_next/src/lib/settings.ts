import { cache } from "react";
import { db } from "./db";

export const DEFAULT_SETTINGS: Record<string, string> = {
  siteName: "سامانه پویا",
  siteShort: "سامانه پویا",
  tagline: "سامانه رسمی — اخبار، اطلاعیه‌ها و خدمات",
  logo: "/images/logo.png",
  address: "",
  phones: "",
  email: "info@example.com",
  presidentName: "",
  presidentPhoto: "",
  aboutText:
    "این سامانه با هدف اطلاع‌رسانی رسمی و ارائه خدمات آنلاین راه‌اندازی شده است؛ اخبار، اطلاعیه‌ها و خدمات در همین سایت منتشر می‌شود.",
  statStudents: "0",
  statFaculty: "0",
  statBooks: "0",
  statPrograms: "0",
  mapUrl: "",
  mapLat: "35.6892",
  mapLng: "51.3890",
  tickerEnabled: "1",
  chatWelcome:
    "سلام! من دستیار هوشمند سایت هستم؛ درباره اخبار، اطلاعیه‌ها، صفحات، آدرس و تلفن‌های تماس می‌توانید از من بپرسید.",
  footerNote:
    "کلیه حقوق این سامانه محفوظ است.",
};

export const getSettings = cache(
  async (): Promise<Record<string, string>> => {
    const map: Record<string, string> = { ...DEFAULT_SETTINGS };
    try {
      const rows = await db.setting.findMany();
      for (const r of rows) {
        if (r.value !== null && r.value !== undefined) map[r.key] = r.value;
      }
    } catch {
      // اگر دیتابیس هنوز آماده نیست، مقادیر پیش‌فرض برگردد
    }
    return map;
  }
);

export function getPhones(settings: Record<string, string>): string[] {
  return (settings.phones || "")
    .split(/[,\n،]/)
    .map((p) => p.trim())
    .filter(Boolean);
}
