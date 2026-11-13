# -*- coding: utf-8 -*-
"""گزارش فارسی کلون به‌صورت Markdown"""
import datetime
import os

from .utils import human_size


def _table(rows):
    if not rows:
        return "_(موردی ثبت نشد)_\n"
    header = "| " + " | ".join(rows[0][0]) + " |"
    sep = "| " + " | ".join(["---"] * len(rows[0][0])) + " |"
    body = []
    for cols, *_ in rows:
        body.append("| " + " | ".join(str(c) for c in cols) + " |")
    return "\n".join([header, sep] + body) + "\n"


def build_report(out_dir, site_info, counts, mirror_summary, wxr_items,
                 media_stats, zip_path=None):
    site = site_info.get("site") or {}
    base = site_info.get("base_url")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# گزارش کلون سایت: {site.get('name') or base}",
        "",
        f"- آدرس اصلی: {base}",
        f"- تاریخ کلون: {now}",
        f"- وردپرس تشخیص داده شد: {'بله' if site_info.get('is_wp') else 'خیر'}",
        f"- نسخه وردپرس: {site_info.get('wp_version') or 'نامشخص'}",
        f"- قالب تشخیص داده شده: {site_info.get('theme') or 'نامشخص'}",
        f"- توضیحات سایت: {site.get('description') or '-'}",
        "",
        "## آمار محتوای دریافت‌شده",
        "",
        _table([
            (("نوع محتوا", "تعداد"),),
            (("نوشته‌ها (posts)", counts.get("posts", 0)),),
            (("برگه‌ها (pages)", counts.get("pages", 0)),),
            (("رسانه‌ها (media)", counts.get("media", 0)),),
            (("دسته‌ها", counts.get("categories", 0)),),
            (("برچسب‌ها", counts.get("tags", 0)),),
            (("دیدگاه‌ها", counts.get("comments", 0)),),
            (("کاربران", counts.get("users", 0)),),
            (("منوها", counts.get("menus", 0)),),
            (("آیتم‌های منو", counts.get("menu_items", 0)),),
            (("انواع سفارشی", sum(v for k, v in counts.items() if k.startswith("cpt_"))),),
            (("تکسونومی‌های سفارشی", sum(v for k, v in counts.items() if k.startswith("tax_"))),),
        ]),
        "## آینه استاتیک",
        "",
        _table([
            (("شاخص", "مقدار"),),
            (("تعداد صفحات", mirror_summary.get("pages", 0)),),
            (("تعداد فایل‌ها (CSS/JS/عکس/فونت)", mirror_summary.get("assets", 0)),),
            (("حجم فایل‌ها", human_size(mirror_summary.get("bytes", 0))),),
            (("دریافت ناموفق صفحه", mirror_summary.get("failed_pages", 0)),),
            (("دریافت ناموفق فایل", mirror_summary.get("failed_assets", 0)),),
        ]),
        "## رسانه‌ها",
        "",
        _table([
            (("شاخص", "مقدار"),),
            (("فایل دانلودشده", media_stats.get("count", 0)),),
            (("حجم", human_size(media_stats.get("bytes", 0))),),
        ]),
        "## خروجی WXR (واردپرس)",
        "",
        f"- مسیر فایل: `wxr/export.xml`",
        f"- تعداد آیتم‌ها: {wxr_items}",
        "",
        "## ساختار خروجی",
        "",
        "```",
        f"{os.path.basename(out_dir.rstrip(os.sep))}/",
        "├── mirror/        آینه استاتیک کامل سایت (index.html را در مرورگر باز کنید)",
        "├── media/         فایل‌های رسانه‌ای دانلودشده",
        "├── api_data/      داده خام JSON هر بخش از REST API",
        "├── wxr/export.xml فایل استاندارد ایمپورت وردپرس",
        "├── clone.zip      همه موارد بالا در یک فایل ZIP",
        "└── report.md      همین گزارش",
        "```",
        "",
        "## گام‌های بعدی",
        "",
        "1. **بازکردن آینه آفلاین:** فایل `mirror/index.html` را در مرورگر باز کنید.",
        "2. **سرو‌کردن آینه:** در پوشه mirror دستور `python -m http.server 8080` را اجرا و به `http://localhost:8080` بروید.",
        "3. **ایمپورت در وردپرس جدید:** در پیشخوان وردپرس مسیر Tools → Import → WordPress را انتخاب کنید، افزونه WordPress Importer را نصب و فایل `wxr/export.xml` را بارگذاری کنید (گزینه Download and import file attachments را بزنید تا رسانه‌ها هم منتقل شوند).",
        "4. توجه: کلون فقط برای سایت‌هایی که مالک آن‌ها هستید یا اجازه دارید استفاده شود.",
        "",
    ]

    path = os.path.join(out_dir, "report.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
