import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/toaster";
import { ThemeProvider } from "@/components/theme-provider";
import { SitePrefsProvider, PREFS_BOOT_SCRIPT } from "@/lib/prefs";
import { getSettings } from "@/lib/settings";

export async function generateMetadata(): Promise<Metadata> {
  let siteName = "سامانه پویا";
  let tagline = "سامانه رسمی — اخبار، اطلاعیه‌ها، گالری و ارتباط با ما";
  try {
    const s = await getSettings();
    if (s.siteName) siteName = s.siteName;
    if (s.tagline) tagline = s.tagline;
  } catch {
    // دیتابیس هنوز آماده نیست
  }
  return {
    title: {
      default: siteName,
      template: `%s | ${siteName}`,
    },
    description: tagline,
    icons: { icon: "/images/logo.png" },
  };
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl" suppressHydrationWarning>
      <body className="antialiased bg-background text-foreground min-h-screen flex flex-col">
        {/* اعمال تنظیمات شخصی‌سازی (زبان، فونت، اندازه و…) قبل از رندر
            — تگ script خام (بدون next/script) تا در HTML اولیه حضور داشته باشد
            و باعث ناهماهنگی hydration نشود */}
        <script
          id="prefs-boot"
          dangerouslySetInnerHTML={{ __html: PREFS_BOOT_SCRIPT }}
        />
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          <SitePrefsProvider>{children}</SitePrefsProvider>
          <Toaster />
        </ThemeProvider>
      </body>
    </html>
  );
}
