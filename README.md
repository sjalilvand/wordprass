# ایجنت کلون سایت‌های وردپرس (WordPress Clone Agent)

ابزار خط فرمان و پنل وب فارسی برای **کلون کامل یک سایت وردپرسی**: محتوای کامل از REST API + آینه استاتیک عین همان سایت + فایل استاندارد WXR برای انتقال به وردپرس جدید + دانلود همه رسانه‌ها + گزارش فارسی.

> **هشدار قانونی:** این ابزار را فقط برای سایت‌هایی استفاده کنید که **مالک آن‌ها هستید** یا اجازه کپی‌کردن محتوایشان را دارید. مسئولیت استفاده نادرست با کاربر است.

## چه چیزی تحویل می‌دهد؟

| خروجی | توضیح |
|---|---|
| `mirror/` | آینه استاتیک کامل سایت (HTML/CSS/JS/عکس/فونت) با لینک‌های بازنویسی‌شده — عین همان طراحی، آفلاین باز می‌شود |
| `media/` | همه فایل‌های رسانه‌ای دانلودشده از کتابخانه رسانه وردپرس |
| `wxr/export.xml` | فایل استاندارد **WXR 1.2** شامل نوشته‌ها، برگه‌ها، دسته‌ها، برچسب‌ها، دیدگاه‌ها، نویسنده‌ها، منوها، انواع محتوای سفارشی و تصاویر شاخص — قابل ایمپورت در هر وردپرس |
| `api_data/` | داده خام JSON هر بخش از REST API (برای استفاده‌های دیگر) |
| `report.md` | گزارش فارسی از آمار و نتایج کلون |
| `clone.zip` | همه موارد بالا در یک فایل ZIP |

قابلیت‌های پشتیبانی‌شده:

- نوشته‌ها، برگه‌ها، تگ‌ها، دسته‌ها، دیدگاه‌ها، کاربران (REST API وردپرس)
- انواع محتوای سفارشی (Custom Post Types) و تکسونومی‌های سفارشی — کشف خودکار
- منوها و آیتم‌های منو (وردپرس ۵.۹ به بالا)
- تصاویر شاخص، تصاویر کوچک چندسایزی (srcset)، فونت‌های داخل CSS
- آینه استاتیک با حفظ ساختار پوشه‌های سایت اصلی و بازنویسی لینک‌ها به مسیر نسبی
- پنل وب محلی با نوار پیشرفت زنده و دکمه دانلود ZIP

## نصب

```bash
git clone https://github.com/sjalilvand/wordprass.git
cd wordprass
pip install -r requirements.txt
```

پایتون ۳.۸ به بالا لازم است.

## استفاده — خط فرمان (CLI)

```bash
# کلون کامل
python wp_clone_agent.py https://example.com

# تست سریع با محدودیت
python wp_clone_agent.py https://example.com --limit 10 --max-pages 30

# فقط آینه استاتیک
python wp_clone_agent.py https://example.com --no-api --no-wxr

# فقط فایل وردپرس و رسانه‌ها (بدون آینه)
python wp_clone_agent.py https://example.com --no-mirror

# اجرای پنل وب
python wp_clone_agent.py --webui
```

مهم‌ترین گزینه‌ها:

| گزینه | پیش‌فرض | توضیح |
|---|---|---|
| `--out` | `./output` | پوشه خروجی |
| `--limit` | بدون حد | حداکثر آیتم هر بخش API (برای تست) |
| `--max-pages` | 300 | حداکثر صفحه HTML برای آینه |
| `--max-assets` | 1500 | حداکثر فایل CSS/JS/عکس برای آینه |
| `--delay` | 0.35 | تأخیر بین درخواست‌ها (ثانیه) — برای احترام به سرور مقصد |
| `--no-mirror` / `--no-api` / `--no-wxr` / `--no-zip` | — | غیرفعال‌کردن هر بخش |

## استفاده — پنل وب

```bash
python wp_clone_agent.py --webui
```

سپس در مرورگر به `http://127.0.0.1:8765` بروید؛ آدرس سایت را وارد کنید، پیشرفت را زنده ببینید و در پایان ZIP را دانلود کنید.

## بعد از کلون چه‌کار کنید؟

**۱) باز کردن آینه آفلاین:**
فایل `output/<site>/mirror/index.html` را در مرورگر باز کنید. برای حالت سرور:
```bash
cd output/<site>/mirror
python -m http.server 8080
# http://localhost:8080
```

**۲) انتقال به وردپرس جدید (حفظ همه قابلیت‌های CMS):**
- در پیشخوان وردپرس جدید: **ابزارها → درون‌ریزی (Tools → Import) → WordPress**
- افزونه WordPress Importer را نصب کنید
- فایل `wxr/export.xml` را بارگذاری کنید
- گزینه **Download and import file attachments** را فعال کنید تا رسانه‌ها منتقل شوند

**۳) ثبت کلون در گیت‌هاب (اختیاری):** خروجی پوشه `output` را داخل ریپوی خودتان کامیت کنید یا فقط ZIP را نگه دارید.

## ساختار پروژه

```
wp_clone_agent.py        نقطه ورود CLI
wpcagent/
├── engine.py            هماهنگ‌کننده کل فرایند
├── detector.py          تشخیص وردپرس و REST API
├── api_scraper.py       دریافت محتوا از REST API (صفحه‌بندی خودکار)
├── media_dl.py          دانلود رسانه‌ها
├── crawler.py           خزنده آینه استاتیک + بازنویسی لینک‌ها
├── wxr_builder.py       سازنده فایل WXR 1.2
├── reporter.py          گزارش فارسی
├── packager.py          ساخت ZIP
└── webui_launcher.py    راه‌انداز پنل وب
webui/app.py             پنل وب Flask + قالب RTL فارسی
```

## عیب‌یابی

| مشکل | راه‌حل |
|---|---|
| «وردپرس تشخیص داده نشد» | REST API ممکن است غیرفعال باشد؛ ابزار فقط آینه می‌سازد. برای فعال‌سازی API افزونه امنیتی سایت را بررسی کنید |
| خطای 429 / محدودیت سرور | `--delay 1` یا بیشتر بگذارید و `--max-pages` را کم کنید |
| برخی فایل‌ها در آینه ناقص‌اند | حد را بالا ببرید: `--max-pages 1000 --max-assets 5000` |
| منوها در فایل WXR نیستند | منوها فقط در وردپرس ۵.۹+ از REST قابل خواندن هستند |
| سایت محافظت Cloudflare دارد | ممکن است درخواست‌ها بلاک شوند؛ سرعت را کم و delay را زیاد کنید |

## محدودیت‌های نسخه فعلی

- محتوای خصوصی/پیش‌نویس و پنل مدیریت کلون نمی‌شود (REST عمومی پایه است)
- افزونه‌های مخصوص (فرم‌ها، فروشگاه ووکامرس به‌صورت داده سفارشی) از طریق CPT کشف می‌شوند ولی منطق سمت سرور آن‌ها طبیعتاً منتقل نمی‌شود — برای آن‌ها فایل WXR را در نصب وردپرس جدید با همان افزونه‌ها ایمپورت کنید
- آینه استاتیک، صفحات سمت سرور (PHP) را اجرا نمی‌کند؛ هرچه در HTML نهایی است عیناً ذخیره می‌شود

## لایسنس

MIT — فایل LICENSE را ببینید.

---

**English (short):** WordPress Clone Agent — a Persian-friendly CLI + local web panel that fully clones a WordPress site: REST API content (posts, pages, media, comments, menus, CPTs), a full static HTML mirror with rewritten relative links, downloadable media, and a standard WXR 1.2 XML export importable via the WordPress Importer. Usage: `python wp_clone_agent.py https://example.com`. Use only on sites you own or have permission to copy (MIT licensed).
