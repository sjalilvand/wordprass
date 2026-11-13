<div dir="rtl">

# ایجنت کلون سایت‌های وردپرس (WordPress Clone Agent) — نسخه ۲

برنامه‌ای با **پنل وب گرافیکی سه‌زبانه (فارسی / English / العربية)** برای **کلون کامل یک سایت وردپرسی** و سپس **ساخت یک سایت حرفه‌ای Next.js از روی همان محتوا** — دقیقاً با همان الگو و امکانات نمونهٔ [uastemdad](https://github.com/sjalilvand/uastemdad):

✅ محتوای کامل REST API + آینه استاتیک عین همان سایت + فایل استاندارد WXR + دانلود همه رسانه‌ها + درصد پیشرفت زنده
✅ **سایت‌ساز حرفه‌ای (مرحله ۴):** پنل ادمین کامل **فارسی**، چندزبانه (فا/EN/AR)، شخصی‌سازی نمایش، دسترسی‌پذیری توان‌خواهان، چت آنلاین هوشمند، اسلایدر، گالری، خبرنامه، آمار بازدید، فرم تماس، عضویت اعضا و اپ موبایل PWA

> **هشدار قانونی:** این ابزار را فقط برای سایت‌هایی استفاده کنید که **مالک آن‌ها هستید** یا اجازه کپی‌کردن محتوایشان را دارید. مسئولیت استفاده نادرست با کاربر است.

## اجرای سریع روی ویندوز (PowerShell)

1. این ریپو را دانلود/کلون کنید و وارد پوشه آن شوید
2. روی فایل **`run.bat` دابل‌کلیک کنید** (یا در PowerShell: `.\run.ps1`)
3. اسکریپت به‌صورت خودکار: پایتون را پیدا/نصب می‌کند → محیط مجازی می‌سازد → وابستگی‌ها را نصب می‌کند → پنل وب را بالا می‌آورد و مرورگر را باز می‌کند
4. در مرورگرِ باز‌شده: آدرس سایت را وارد کنید، درصد پیشرفت را ببینید و در پایان راهنمای اجرا + دکمه دانلود ZIP نمایش داده می‌شود

پورت پیش‌فرض 8765 است؛ برای تغییر: `powershell -ExecutionPolicy Bypass -File run.ps1 -Port 9000`

## خروجی‌های کلون

| خروجی | توضیح |
|---|---|
| `mirror/` | آینه استاتیک کامل سایت (HTML/CSS/JS/عکس/فونت) با لینک‌های بازنویسی‌شده — عین همان طراحی، آفلاین باز می‌شود |
| `media/` | همه فایل‌های رسانه‌ای دانلودشده |
| `wxr/export.xml` | فایل استاندارد **WXR 1.2** شامل نوشته‌ها، برگه‌ها، دسته‌ها، برچسب‌ها، دیدگاه‌ها، نویسنده‌ها، منوها، انواع محتوای سفارشی و تصاویر شاخص |
| `api_data/` | داده خام JSON هر بخش از REST API |
| `report.md` | گزارش آمار کلون |
| `clone.zip` | همه موارد بالا در یک فایل ZIP |

## محیط گرافیکی (سه مرحله + مرحله ۴ سایت‌ساز حرفه‌ای)

1. **فرم:** وارد کردن آدرس سایت + انتخاب بخش‌ها (آینه/API/WXR/ZIP) + محدودیت‌ها — با انتخاب زبان فارسی/انگلیسی/عربی در بالای صفحه
2. **پیشرفت زنده:** حلقه درصد گرافیکی + مراحل رنگی + لاگ زنده
3. **نتیجه و راهنما:** آمار کلون + دکمه دانلود ZIP + **دکمه پیش‌نمایش سایت** + راهنمای گام‌به‌گام اجرا با دکمه کپی دستورها
4. **سایت‌ساز حرفه‌ای:** گرفتن نام سایت، مسیر ساخت پروژه، زبان‌های سایت، نام کاربری/رمز ادمین، چت آنلاین، آدرس گیت و توکن از کاربر → ساخت یک **سایت کامل Next.js + SQLite از محتوای واقعی کلون‌شده** → نصب خودکار وابستگی‌ها و دیتابیس (اگر Node.js نصب باشد) → اجرای زنده با یک کلیک → کامیت و push به گیت (اختیاری)

## سایت حرفه‌ای که ایجنت می‌سازد (مرحله ۴) — همان الگوی uastemdad

| بخش | امکانات |
|---|---|
| **صفحات عمومی** | صفحه اصلی با اسلایدر، دسترسی سریع، اخبار/اطلاعیه‌ها با جستجو و صفحه‌بندی، نوار خبری متحرک، آمار متحرک، گالری با لایت‌باکس، رسانه و ویدیو، پرسش‌های متداول، تقویم رویدادها، فرم‌ها و اسناد، نقشه و مسیریابی، تقویم شمسی، خواندن متن (TTS)، جستجو، اپ موبایل PWA با کد QR |
| **پنل ادمین (کاملاً فارسی)** | `/admin` — داشبورد آماری، مدیریت اخبار/اطلاعیه‌ها با ویرایشگر و تصویر شاخص، صفحات، دسته‌بندی‌ها، اسلایدر، گالری، منوها، پیوندها، سامانه‌ها، ویدیوها، پرسش‌های متداول، رویدادها، اعضا، مشترکان خبرنامه، صندوق پیام‌ها، آمار بازدید با نمودار، تنظیمات کامل و مدیریت کاربران |
| **چندزبانه** | فارسی / English / العربية با تغییر جهت RTL/LTR، ترجمه کامل رابط و ترجمه خودکار/دستی محتوا از پنل |
| **شخصی‌سازی** | تغییر فونت، ۴ اندازه متن، ۵ رنگ پس‌زمینه، ۷ تم رنگی، تم روشن/تاریک — ذخیره خودکار در مرورگر |
| **دسترسی‌پذیری (توان‌خواه)** | کنتراست بالا، بزرگ‌نمایی متن، زیرخط لینک‌ها، کاهش حرکت، فاصله سطر بیشتر، حالت شب — با دکمه شناور اختصاصی |
| **چت آنلاین هوشمند** | دستیار گفتگو با پاسخ بر اساس داده‌های خود سایت (اخبار، صفحات، تماس) + موتور محلی جایگزین + تاریخچه گفتگو |
| **اعضا و خبرنامه** | ثبت‌نام اعضا با تأیید مدیر، پنل اختصاصی عضو، خبرنامه با مدیریت مشترکان |
| **گیت** | در صورت دادن آدرس ریپو و توکن: init، commit و push خودکار — توکن در هیچ فایلی ذخیره نمی‌شود |

### اجرای سایت ساخته‌شده

- **همان لحظه:** دکمه «اجرا و نمایش زنده سایت» در پنل — پنل ادمین روی `/admin`
- **در آینده (ویندوز):** در پوشه پروژه `START-SITE.bat` را دابل‌کلیک کنید (یا `.\setup.ps1` در PowerShell) — سایت روی `http://localhost:3003`
- **نیازمندی سایت‌ساز:** Node.js نسخه ۲۰ به بالا (اسکریپت setup.ps1 در نبود آن، از winget نصب می‌کند)

> **نکته امنیتی مهم:** دستور `python -m http.server` را فقط داخل پوشه mirror اجرا کنید؛ اجرای آن در ریشه درایو (مثل `D:\`) **کل دیسک شما را روی شبکه باز می‌کند**. برای همین در پنل دکمه «پیش‌نمایش سایت» اضافه شده که نیازی به http.server ندارد.

## نصب و اجرا با خط فرمان (همه سیستم‌عامل‌ها)

```bash
git clone https://github.com/sjalilvand/wordprass.git
cd wordprass
pip install -r requirements.txt

# پنل وب گرافیکی (پیشنهادی)
python wp_clone_agent.py --webui

# یا کلون مستقیم از CLI
python wp_clone_agent.py https://example.com --limit 10 --max-pages 30
```

پایتون ۳.۸ به بالا لازم است؛ برای مرحله سایت‌ساز، Node.js ۲۰ به بالا (اختیاری ولی پیشنهادی).

### گزینه‌های CLI

| گزینه | پیش‌فرض | توضیح |
|---|---|---|
| `--out` | `./output` | پوشه خروجی |
| `--limit` | بدون حد | حداکثر آیتم هر بخش API |
| `--max-pages` | 300 | حداکثر صفحه HTML برای آینه |
| `--max-assets` | 1500 | حداکثر فایل برای آینه |
| `--delay` | 0.35 | تأخیر بین درخواست‌ها (ثانیه) |
| `--no-mirror` / `--no-api` / `--no-wxr` / `--no-zip` | — | غیرفعال‌کردن هر بخش |
| `--webui --port 8765` | — | اجرای پنل وب گرافیکی |

## بعد از کلون چه‌کار کنید؟ (خلاصه)

1. **پیش‌نمایش سریع:** در پنل، دکمه «پیش‌نمایش سایت» را بزنید (بدون هیچ دستوری)
2. **آفلاین:** فایل `mirror/index.html` را در مرورگر باز کنید
3. **سرور محلی:** در پوشه mirror → `python -m http.server 8080` → مرورگر: `http://localhost:8080` (فقط داخل همین پوشه!)
4. **سایت حرفه‌ای کامل:** در پنل، مرحله ۴ «ساخت سایت حرفه‌ای» را پر کنید → نصب و اجرای زنده خودکار
5. **وردپرس جدید:** پیشخوان → Tools → Import → WordPress → نصب افزونه Importer → بارگذاری `wxr/export.xml` (تیک دانلود فایل‌های پیوست)

## ساختار پروژه

```
run.bat / run.ps1                  اجرای یک‌کلیکی ویندوز (PowerShell)
wp_clone_agent.py                  نقطه ورود CLI
wpcagent/                          هسته برنامه (engine, detector, api_scraper,
                                   media_dl, crawler, wxr_builder, reporter, packager)
wpcagent/next_builder.py           سایت‌ساز حرفه‌ای Next.js (ساخت seed از محتوای کلون،
                                   نصب خودکار، push گیت)
wpcagent/site_template_next/       قالب کامل سایت Next.js (الگوی uastemdad:
                                   پنل ادمین فارسی، چندزبانه، چت، PWA، …)
webui/app.py                       پنل وب Flask + قالب سه‌زبانه RTL/LTR + سایت‌ساز + پیش‌نمایش زنده
```

## عیب‌یابی

| مشکل | راه‌حل |
|---|---|
| PowerShell اجرا نمی‌کند | از `run.bat` استفاده کنید یا `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| پایتون پیدا نشد | پایتون را از python.org نصب کنید و تیک «Add Python to PATH» را بزنید |
| «وردپرس تشخیص داده نشد» | REST API سایت غیرفعال است؛ فقط آینه ساخته می‌شود |
| خطای 429 / محدودیت سرور | `--delay 1` و کم‌کردن `--max-pages` |
| Node.js برای سایت‌ساز ندارید | تیک «نصب خودکار» را بردارید؛ بعداً `START-SITE.bat` در پوشه پروژه همه‌چیز را نصب و اجرا می‌کند |
| نصب npm طولانی است | طبیعی است (اولین بار فقط یک‌بار)؛ دفعات بعد فوری است |
| منوها در WXR نیستند | منوها فقط در وردپرس ۵.۹+ از REST قابل خواندن هستند |
| push گیت نشد | آدرس ریپو و توکن را بررسی کنید؛ توکن باید اجازه push به آن ریپو را داشته باشد |

## لایسنس

MIT — فایل LICENSE را ببینید.

</div>

---

<div dir="ltr">

# WordPress Clone Agent (English) — v2

A trilingual (FA/EN/AR) graphical web panel that **fully clones a WordPress site**, then **builds a professional Next.js site from the cloned content** — the exact blueprint of the [uastemdad](https://github.com/sjalilvand/uastemdad) sample: Persian admin panel, multilingual (FA/EN/AR), display personalization, accessibility toolkit, smart online chat, slider, gallery, newsletter, visit stats, contact form, membership and PWA mobile app.

## Quick start (Windows)
Double-click **`run.bat`** (or `.\run.ps1`). The script finds/installs Python, creates a venv, installs requirements, starts the web panel and opens your browser at `http://127.0.0.1:8765`.

## Quick start (macOS / Linux)
```bash
pip install -r requirements.txt
python wp_clone_agent.py --webui          # graphical panel
python wp_clone_agent.py https://example.com   # direct CLI clone
```

## Outputs
`mirror/` exact offline HTML copy — `media/` all downloads — `wxr/export.xml` standard WXR 1.2 importable via WordPress Tools → Import — `api_data/` raw JSON — `report.md` — `clone.zip`.

## Step 4: Professional site builder
Enter site name, project folder, site languages, admin credentials, online chat toggle, optional Git repo + token → the agent generates a **complete Next.js 16 + TypeScript + Tailwind + Prisma + SQLite site seeded with the real cloned content**: rich Persian admin panel (`/admin`), multilingual UI with auto translation, personalization (fonts/sizes/backgrounds/7 color themes), accessibility (high contrast, text zoom, reduced motion), smart chat widget with a local answer engine, news ticker, hero slider, lightbox gallery, media/video page, FAQ, events calendar, Jalali calendar, TTS read-aloud, contact form, newsletter, member area with admin approval, visit analytics and a PWA installable mobile app. It can run `npm install`, `prisma db push` and seed automatically (Node.js 20+ required — `START-SITE.bat` installs it via winget if missing), start a live preview with one click, and `git init/commit/push` — the token is never stored in any file.

## Run the cloned site
1. Panel button **Preview** (no manual server needed), or open `mirror/index.html` in a browser (offline), or
2. Serve it: `cd mirror && python -m http.server 8080` → http://localhost:8080 (run it **only inside the mirror folder** — never at a drive root!)
3. Full CMS on a new WordPress: Tools → Import → WordPress → upload `wxr/export.xml` (+ attachments option).
4. Generated Next.js site: double-click `START-SITE.bat` in the project folder → http://localhost:3003 (admin at `/admin`).

> Legal: use only on sites you own or have permission to copy. MIT license.

</div>

---

<div dir="rtl" lang="ar">

# وكيل استنساخ مواقع ووردبريس (العربية) — الإصدار ٢

لوحة ويب رسومية بثلاث لغات (الفارسية / English / العربية) **لاستنساخ موقع ووردبريس بالكامل ثم بناء موقع Next.js احترافي من المحتوى المستنسخ** — وفق النموذج نفسه للمثال [uastemdad](https://github.com/sjalilvand/uastemdad): لوحة إدارة فارسية كاملة، تعدد اللغات، تخصيص العرض، أدوات إمكانية الوصول، دردشة ذكية مباشرة، سلايدر، معرض صور، نشرة بريدية، إحصاءات الزيارات، نموذج تواصل، عضوية الأعضاء وتطبيق PWA.

## البدء السريع (ويندوز)
انقر نقراً مزدوجاً على **`run.bat`** (أو نفّذ `.\run.ps1`). سيجد السكربت بايثون أو يثبّته، وينشئ البيئة الافتراضية، ويثبّت المتطلبات، ويشغّل اللوحة على `http://127.0.0.1:8765`.

## البدء السريع (ماك / لينكس)
```bash
pip install -r requirements.txt
python wp_clone_agent.py --webui
python wp_clone_agent.py https://example.com
```

## المخرجات
`mirror/` نسخة HTML مطابقة تعمل دون اتصال — `media/` كل التنزيلات — `wxr/export.xml` ملف WXR 1.2 يُستورد من الأدوات → استيراد → WordPress — `api_data/` JSON خام — `report.md` — `clone.zip`.

## الخطوة ٤: منشئ الموقع الاحترافي
أدخل اسم الموقع ومجلد المشروع ولغات الموقع وبيانات المدير ورابط Git والرمز ← يبني الوكيل **موقع Next.js كامل معبأ بالمحتوى الحقيقي المستنسخ**: لوحة إدارة فارسية كاملة (`/admin`)، تعدد اللغات مع ترجمة تلقائية، تخصيص العرض (خطوط/أحجام/ألوان/٧ ثيمات)، إمكانية الوصول، دردشة ذكية مع محرك محلي، شريط أخبار متحرك، سلايدر، معرض صور، صفحة وسائط وفيديو، أسئلة متحولة، تقويم الأحداث، تقويم جلالي، قراءة نصية صوتية، نموذج تواصل، نشرة بريدية، منطقة أعضاء بإدارة الموافقات، تحليلات الزيارات وتطبيق PWA. يشغّل `npm install` و `prisma db push` والـ seed تلقائياً (يتطلب Node.js 20+)، ويعرض معاينة حية بنقرة واحدة، ويدفع إلى Git تلقائياً — ولا يُحفظ الرمز في أي ملف.

## تشغيل الموقع المستنسخ
1. افتح `mirror/index.html` في المتصفح، أو
2. شغّله كخادم: `cd mirror && python -m http.server 8080` → http://localhost:8080
3. CMS كامل على ووردبريس جديد: الأدوات → استيراد → WordPress → ارفع `wxr/export.xml`.
4. موقع Next.js المولَّد: انقر مرتين على `START-SITE.bat` في مجلد المشروع → http://localhost:3003 (لوحة الإدارة على `/admin`).

> قانوني: استخدمه فقط للمواقع التي تملكها أو لديك إذن بنسخها. رخصة MIT.

</div>
