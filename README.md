<div dir="rtl">

# ایجنت کلون سایت‌های وردپرس (WordPress Clone Agent)

برنامه‌ای با **پنل وب گرافیکی سه‌زبانه (فارسی / English / العربية)** برای **کلون کامل یک سایت وردپرسی**: محتوای کامل از REST API + آینه استاتیک عین همان سایت + فایل استاندارد WXR برای انتقال به وردپرس جدید + دانلود همه رسانه‌ها + درصد پیشرفت زنده + راهنمای اجرای سایت در پایان کار.

> **هشدار قانونی:** این ابزار را فقط برای سایت‌هایی استفاده کنید که **مالک آن‌ها هستید** یا اجازه کپی‌کردن محتوایشان را دارید. مسئولیت استفاده نادرست با کاربر است.

## اجرای سریع روی ویندوز (PowerShell)

1. این ریپو را دانلود/کلون کنید و وارد پوشه آن شوید
2. روی فایل **`run.bat` دابل‌کلیک کنید** (یا در PowerShell: `powershell -ExecutionPolicy Bypass -File run.ps1`)
3. اسکریپت به‌صورت خودکار: پایتون را پیدا/نصب می‌کند → محیط مجازی می‌سازد → وابستگی‌ها را نصب می‌کند → پنل وب را بالا می‌آورد و مرورگر را باز می‌کند
4. در مرورگرِ باز‌شده: آدرس سایت را وارد کنید، درصد پیشرفت را ببینید و در پایان راهنمای اجرا + دکمه دانلود ZIP نمایش داده می‌شود

پورت پیش‌فرض 8765 است؛ برای تغییر: `powershell -ExecutionPolicy Bypass -File run.ps1 -Port 9000`

## خروجی‌ها

| خروجی | توضیح |
|---|---|
| `mirror/` | آینه استاتیک کامل سایت (HTML/CSS/JS/عکس/فونت) با لینک‌های بازنویسی‌شده — عین همان طراحی، آفلاین باز می‌شود |
| `media/` | همه فایل‌های رسانه‌ای دانلودشده |
| `wxr/export.xml` | فایل استاندارد **WXR 1.2** شامل نوشته‌ها، برگه‌ها، دسته‌ها، برچسب‌ها، دیدگاه‌ها، نویسنده‌ها، منوها، انواع محتوای سفارشی و تصاویر شاخص |
| `api_data/` | داده خام JSON هر بخش از REST API |
| `report.md` | گزارش آمار کلون |
| `clone.zip` | همه موارد بالا در یک فایل ZIP |

## محیط گرافیکی (سه مرحله)

1. **فرم:** وارد کردن آدرس سایت + انتخاب بخش‌ها (آینه/API/WXR/ZIP) + محدودیت‌ها — با انتخاب زبان فارسی/انگلیسی/عربی در بالای صفحه
2. **پیشرفت زنده:** حلقه درصد گرافیکی + مراحل رنگی (تشخیص → محتوا → رسانه → آینه → XML → گزارش → ZIP) + لاگ زنده
3. **نتیجه و راهنما:** آمار کلون + دکمه دانلود ZIP + راهنمای گام‌به‌گام اجرای سایت (بازکردن آینه، سرور محلی، ایمپورت وردپرس) با دکمه کپی دستورها

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

پایتون ۳.۸ به بالا لازم است.

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

1. **آفلاین:** فایل `mirror/index.html` را در مرورگر باز کنید
2. **سرور محلی:** در پوشه mirror → `python -m http.server 8080` → مرورگر: `http://localhost:8080`
3. **وردپرس جدید:** پیشخوان → Tools → Import → WordPress → نصب افزونه Importer → بارگذاری `wxr/export.xml` (تیک دانلود فایل‌های پیوست)

## ساختار پروژه

```
run.bat / run.ps1        اجرای یک‌کلیکی ویندوز (PowerShell)
wp_clone_agent.py        نقطه ورود CLI
wpcagent/                هسته برنامه (engine, detector, api_scraper,
                         media_dl, crawler, wxr_builder, reporter, packager)
webui/app.py             پنل وب Flask + قالب سه‌زبانه RTL/LTR
```

## عیب‌یابی

| مشکل | راه‌حل |
|---|---|
| PowerShell اجرا نمی‌کند | از `run.bat` استفاده کنید یا `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| پایتون پیدا نشد | پایتون را از python.org نصب کنید و تیک «Add Python to PATH» را بزنید |
| «وردپرس تشخیص داده نشد» | REST API سایت غیرفعال است؛ فقط آینه ساخته می‌شود |
| خطای 429 / محدودیت سرور | `--delay 1` و کم‌کردن `--max-pages` |
| منوها در WXR نیستند | منوها فقط در وردپرس ۵.۹+ از REST قابل خواندن هستند |

## لایسنس

MIT — فایل LICENSE را ببینید.

</div>

---

<div dir="ltr">

# WordPress Clone Agent (English)

A trilingual (FA/EN/AR) graphical web panel that **fully clones a WordPress site**: REST API content + exact static HTML mirror + standard WXR XML export + all media downloads + live progress percentage + final step-by-step guide to run the cloned site.

## Quick start (Windows)
Double-click **`run.bat`** (or `powershell -ExecutionPolicy Bypass -File run.ps1`). The script finds/installs Python, creates a venv, installs requirements, starts the web panel and opens your browser at `http://127.0.0.1:8765`.

## Quick start (macOS / Linux)
```bash
pip install -r requirements.txt
python wp_clone_agent.py --webui          # graphical panel
python wp_clone_agent.py https://example.com   # direct CLI clone
```

## Outputs
`mirror/` exact offline HTML copy — `media/` all downloads — `wxr/export.xml` standard WXR 1.2 importable via WordPress Tools → Import — `api_data/` raw JSON — `report.md` — `clone.zip`.

## Run the cloned site
1. Open `mirror/index.html` in a browser (offline), or
2. Serve it: `cd mirror && python -m http.server 8080` → http://localhost:8080
3. Full CMS on a new WordPress: Tools → Import → WordPress → upload `wxr/export.xml` (+ attachments option).

> Legal: use only on sites you own or have permission to copy. MIT license.

</div>

---

<div dir="rtl" lang="ar">

# وكيل استنساخ مواقع ووردبريس (العربية)

لوحة ويب رسومية بثلاث لغات (الفارسية / English / العربية) **لاستنساخ موقع ووردبريس بالكامل**: محتوى REST API + مرآة HTML ثابتة مطابقة + ملف WXR القياسي + تنزيل كل الوسائط + نسبة تقدم حية + دليل خطوة بخطوة لتشغيل الموقع المستنسخ.

## البدء السريع (ويندوز)
انقر نقراً مزدوجاً على **`run.bat`** (أو نفّذ `powershell -ExecutionPolicy Bypass -File run.ps1`). سيجد السكربت بايثون أو يثبّته، وينشئ البيئة الافتراضية، ويثبّت المتطلبات، ويشغّل اللوحة على `http://127.0.0.1:8765`.

## البدء السريع (ماك / لينكس)
```bash
pip install -r requirements.txt
python wp_clone_agent.py --webui
python wp_clone_agent.py https://example.com
```

## المخرجات
`mirror/` نسخة HTML مطابقة تعمل دون اتصال — `media/` كل التنزيلات — `wxr/export.xml` ملف WXR 1.2 يُستورد من الأدوات → استيراد → WordPress — `api_data/` JSON خام — `report.md` — `clone.zip`.

## تشغيل الموقع المستنسخ
1. افتح `mirror/index.html` في المتصفح، أو
2. شغّله كخادم: `cd mirror && python -m http.server 8080` → http://localhost:8080
3. CMS كامل على ووردبريس جديد: الأدوات → استيراد → WordPress → ارفع `wxr/export.xml`.

> قانوني: استخدمه فقط للمواقع التي تملكها أو لديك إذن بنسخها. رخصة MIT.

</div>
