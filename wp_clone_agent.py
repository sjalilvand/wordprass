#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ایجنت کلون سایت‌های وردپرس
WordPress Clone Agent — CLI

استفاده:
    python wp_clone_agent.py https://example.com
    python wp_clone_agent.py https://example.com --limit 5 --max-pages 20
    python wp_clone_agent.py --webui
"""
import argparse
import sys

from wpcagent.engine import run_clone
from wpcagent.utils import setup_logging


def build_parser():
    p = argparse.ArgumentParser(
        prog="wp_clone_agent",
        description="کلون کامل یک سایت وردپرسی: آینه استاتیک + فایل WXR + رسانه‌ها + گزارش",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "مثال‌ها:\n"
            "  python wp_clone_agent.py https://example.com\n"
            "  python wp_clone_agent.py https://example.com --limit 10 --max-pages 30\n"
            "  python wp_clone_agent.py https://example.com --no-mirror --no-zip\n"
            "  python wp_clone_agent.py --webui --port 8765\n"
        ),
    )
    p.add_argument("url", nargs="?", help="آدرس سایت وردپرسی موردنظر")
    p.add_argument("--out", default=None, help="پوشه خروجی (پیش‌فرض: ./output)")
    p.add_argument("--limit", type=int, default=None,
                   help="حداکثر تعداد آیتم هر بخش از REST API (بدون حد: خالی بگذارید)")
    p.add_argument("--max-pages", type=int, default=300,
                   help="حداکثر تعداد صفحه HTML برای آینه (پیش‌فرض: 300)")
    p.add_argument("--max-assets", type=int, default=1500,
                   help="حداکثر تعداد فایل CSS/JS/عکس برای آینه (پیش‌فرض: 1500)")
    p.add_argument("--delay", type=float, default=0.35,
                   help="تأخیر بین درخواست‌ها به ثانیه (پیش‌فرض: 0.35)")
    p.add_argument("--no-api", action="store_true", help="غیرفعال‌کردن دریافت REST API")
    p.add_argument("--no-media", action="store_true", help="غیرفعال‌کردن دانلود رسانه‌ها")
    p.add_argument("--no-mirror", action="store_true", help="غیرفعال‌کردن آینه استاتیک")
    p.add_argument("--no-wxr", action="store_true", help="غیرفعال‌کردن ساخت فایل WXR")
    p.add_argument("--no-zip", action="store_true", help="غیرفعال‌کردن ساخت ZIP")
    p.add_argument("--verbose", action="store_true", help="نمایش پیام‌های کامل دیباگ")
    p.add_argument("--webui", action="store_true",
                   help="اجرای پنل وب محلی به‌جای خط فرمان")
    p.add_argument("--port", type=int, default=8765, help="پورت پنل وب (پیش‌فرض: 8765)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.webui:
        from wpcagent.webui_launcher import launch_webui
        launch_webui(port=args.port)
        return 0

    if not args.url:
        build_parser().print_help()
        print("\n[!] آدرس سایت را وارد کنید؛ مثال: python wp_clone_agent.py https://example.com")
        return 1

    setup_logging(args.verbose)
    summary = run_clone(
        args.url,
        out_root=args.out,
        do_api=not args.no_api,
        do_media=not args.no_media,
        do_mirror=not args.no_mirror,
        do_wxr=not args.no_wxr,
        do_zip=not args.no_zip,
        limit=args.limit,
        max_pages=args.max_pages,
        max_assets=args.max_assets,
        delay=args.delay,
        verbose=args.verbose,
    )

    print()
    print("خلاصه نتیجه:")
    print(f"  وردپرسی: {'بله' if summary.get('is_wp') else 'خیر'}")
    counts = summary.get("counts") or {}
    for key in ("posts", "pages", "media", "categories", "tags", "comments"):
        if key in counts:
            print(f"  {key}: {counts[key]}")
    print(f"  صفحات آینه: {summary.get('mirror', {}).get('pages', 0)}")
    print(f"  فایل‌های آینه: {summary.get('mirror', {}).get('assets', 0)}")
    print(f"  آیتم‌های WXR: {summary.get('wxr_items', 0)}")
    if summary.get("errors"):
        print(f"  خطاها: {summary['errors']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
