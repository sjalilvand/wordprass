import { PrismaClient } from "@prisma/client";

/**
 * Seed جایگزین‌شدنی — سایت‌ساز «ایجنت کلون وردپرس» این فایل را
 * به‌صورت خودکار با داده‌های واقعی سایت کلون‌شده بازنویسی می‌کند.
 */
const db = new PrismaClient();

async function main() {
  if ((await db.user.count()) > 0 && process.env.SEED_FORCE !== "1") {
    console.log("↩ نصب قبلی شناسایی شد — داده‌ها حفظ شدند");
    return;
  }
  console.log("→ seed placeholder — توسط سایت‌ساز بازنویسی خواهد شد");
  const { hashPassword } = await import("../src/lib/auth");
  await db.user.create({
    data: { username: "admin", passwordHash: hashPassword("admin123"), name: "مدیر سامانه", role: "ADMIN" },
  });
  const { DEFAULT_SETTINGS } = await import("../src/lib/settings");
  for (const [key, value] of Object.entries(DEFAULT_SETTINGS)) {
    await db.setting.create({ data: { key, value } });
  }
  console.log("✅ Seed پایه انجام شد");
}

main()
  .catch((e) => { console.error(e); process.exit(1); })
  .finally(async () => { await db.$disconnect(); });
