# -*- coding: utf-8 -*-
"""
هماهنگ‌کننده اصلی کلون: تشخیص → REST API → رسانه → آینه → WXR → گزارش → ZIP
"""
import os
import re

from .utils import log, normalize_url, build_session, human_size
from .detector import detect_wordpress
from .api_scraper import scrape_site
from .media_dl import download_media
from .crawler import crawl_mirror
from .wxr_builder import build_wxr
from .reporter import build_report
from .packager import make_zip


def _host_dirname(url):
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.replace("https://", "").replace("http://", ""))
    return name.strip("_") or "site"


def run_clone(
    target_url,
    out_root=None,
    do_api=True,
    do_media=True,
    do_mirror=True,
    do_wxr=True,
    do_zip=True,
    limit=None,
    max_pages=300,
    max_assets=1500,
    delay=0.35,
    verbose=False,
    progress_cb=None,
):
    """
    اجرای کامل کلون یک سایت وردپرسی.
    progress_cb: تابع callback(percent:int, message:str) برای نمایش پیشرفت
    خروجی: dict خلاصه نتیجه
    """
    setup_ok = log.handlers or None
    if not log.handlers:
        from .utils import setup_logging
        setup_logging(verbose)
    if verbose:
        log.setLevel(10)

    cb = progress_cb or (lambda p, m: None)
    errors = []
    summary = {"ok": False, "counts": {}, "paths": {}, "errors": errors}

    base_url = normalize_url(target_url)
    if out_root is None:
        out_root = os.path.join(os.getcwd(), "output")
    out_dir = os.path.join(out_root, _host_dirname(base_url))
    os.makedirs(out_dir, exist_ok=True)
    summary["paths"]["root"] = out_dir

    log.info("=" * 60)
    log.info("ایجنت کلون وردپرس | هدف: %s", base_url)
    log.info("=" * 60)

    session = build_session()

    # ۱) تشخیص
    cb(5, "تشخیص وردپرس بودن سایت...")
    info = detect_wordpress(session, base_url)
    summary["site"] = info.get("site", {})
    summary["wp_version"] = info.get("wp_version")
    summary["theme"] = info.get("theme")
    summary["is_wp"] = info.get("is_wp")

    if info["is_wp"]:
        site_name = (info.get("site") or {}).get("name") or ""
        log.info("[OK] سایت وردپرسی است | نام: %s | نسخه: %s | قالب: %s",
                 site_name or "نامشخص", info.get("wp_version") or "نامشخص",
                 info.get("theme") or "نامشخص")
    else:
        log.warning("[!] وردپرس تشخیص داده نشد؛ فقط آینه استاتیک ساخته می‌شود")

    # ۲) REST API
    data = {}
    counts = {}
    if info["is_wp"] and do_api:
        cb(10, "دریافت محتوا از REST API...")
        try:
            data, counts = scrape_site(session, info, out_dir,
                                       limit=limit, delay=delay)
        except Exception as e:  # noqa: BLE001
            log.warning("[!] خطا در دریافت REST API: %s", e)
            errors.append("api: " + str(e))
    elif not info["is_wp"]:
        data, counts = {}, {}

    # ۳) رسانه‌ها
    media_stats = {"count": 0, "bytes": 0}
    if info["is_wp"] and do_media and data.get("media"):
        cb(30, "دانلود رسانه‌ها...")
        try:
            _map, ok_count, total_bytes = download_media(
                session, data.get("media"), os.path.join(out_dir, "media"),
                delay=delay, progress_cb=lambda p, m: cb(30 + int(p * 0.15), m))
            media_stats = {"count": ok_count, "bytes": total_bytes}
        except Exception as e:  # noqa: BLE001
            log.warning("[!] خطا در دانلود رسانه‌ها: %s", e)
            errors.append("media: " + str(e))

    # ۴) آینه استاتیک
    mirror_summary = {}
    if do_mirror:
        cb(45, "ساخت آینه استاتیک سایت...")
        try:
            mirror_summary = crawl_mirror(
                session, base_url, os.path.join(out_dir, "mirror"),
                max_pages=max_pages, max_assets=max_assets, delay=delay,
                progress_cb=cb,
            )
        except Exception as e:  # noqa: BLE001
            log.warning("[!] خطا در ساخت آینه: %s", e)
            errors.append("mirror: " + str(e))
    summary["mirror"] = mirror_summary

    # ۵) WXR
    wxr_items = 0
    if info["is_wp"] and do_wxr and data:
        cb(90, "ساخت فایل WXR وردپرس...")
        try:
            wxr_dir = os.path.join(out_dir, "wxr")
            os.makedirs(wxr_dir, exist_ok=True)
            wxr_items = build_wxr(info, data, os.path.join(wxr_dir, "export.xml"))
        except Exception as e:  # noqa: BLE001
            log.warning("[!] خطا در ساخت WXR: %s", e)
            errors.append("wxr: " + str(e))
    summary["wxr_items"] = wxr_items

    # ۶) گزارش
    cb(95, "تولید گزارش...")
    try:
        report_path = build_report(out_dir, info, counts, mirror_summary,
                                   wxr_items, media_stats)
        summary["paths"]["report"] = report_path
        log.info("[OK] گزارش نوشته شد: report.md")
    except Exception as e:  # noqa: BLE001
        log.warning("[!] خطا در تولید گزارش: %s", e)
        errors.append("report: " + str(e))

    # ۷) ZIP
    if do_zip:
        cb(97, "ساخت فایل ZIP...")
        try:
            zip_path = make_zip(out_dir)
            summary["paths"]["zip"] = zip_path
        except Exception as e:  # noqa: BLE001
            log.warning("[!] خطا در ساخت ZIP: %s", e)
            errors.append("zip: " + str(e))

    # خلاصه نهایی
    total_items = sum(counts.values())
    summary["counts"] = counts
    summary["ok"] = True
    cb(100, "کلون کامل شد")
    log.info("-" * 60)
    log.info("پایان کار | آیتم‌های API: %s | صفحات آینه: %s | فایل‌ها: %s | رسانه: %s (%s)",
             total_items, mirror_summary.get("pages", 0),
             mirror_summary.get("assets", 0),
             media_stats.get("count", 0), human_size(media_stats.get("bytes", 0)))
    log.info("خروجی: %s", out_dir)
    if summary["paths"].get("zip"):
        log.info("ZIP: %s", summary["paths"]["zip"])
    log.info("-" * 60)
    return summary
