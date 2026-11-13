# -*- coding: utf-8 -*-
"""ابزارهای کمکی مشترک ایجنت کلون وردپرس"""
import logging
import os
import re
import sys
import time
from urllib.parse import unquote, urlparse

import requests
from requests.adapters import HTTPAdapter, Retry

log = logging.getLogger("wp-clone-agent")

DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 WPCloneAgent/1.0"
)

REQUEST_TIMEOUT = 45


def setup_logging(verbose=False):
    """راه‌اندازی لاگ فارسی روی stdout"""
    for h in list(log.handlers):
        log.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.DEBUG if verbose else logging.INFO)
    log.propagate = False
    return log


def build_session():
    """ساخت سشن HTTP با تلاش مجدد و User-Agent مرورگر"""
    s = requests.Session()
    s.headers.update({
        "User-Agent": DEFAULT_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fa,en;q=0.8",
    })
    retry = Retry(
        total=3,
        connect=3,
        read=2,
        backoff_factor=1.2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


def normalize_url(url):
    """افزودن پروتکل و حذف اسلش انتهایی"""
    url = str(url).strip().strip('"\'')
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url.rstrip("/")


def host_of(url):
    p = urlparse(url)
    return (p.netloc or "").lower()


def host_key(url):
    """میزبان بدون www برای مقایسه"""
    return host_of(url).removeprefix("www.")


def sanitize_filename(name, max_len=120):
    """تبدیل هر رشته به نام فایل امن"""
    name = unquote(str(name))
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", name)
    name = name.strip("._ ")
    if not name:
        name = "file"
    if len(name) > max_len:
        root, ext = os.path.splitext(name)
        ext = ext[:16]
        name = root[: max(1, max_len - len(ext))] + ext
    return name


def human_size(num):
    """حجم خوانا برای انسان"""
    try:
        num = int(num)
    except (TypeError, ValueError):
        return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(num) < 1024.0:
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} TB"


def polite_sleep(delay):
    if delay and delay > 0:
        time.sleep(delay)


def dir_size_bytes(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def safe_relpath(url_path):
    """تبدیل مسیر URL به مسیر نسبی امن روی دیسک (بدون خروج از پوشه)"""
    parts = []
    for seg in unquote(url_path or "").split("/"):
        if seg in ("", ".", ".."):
            continue
        parts.append(sanitize_filename(seg, max_len=80))
    return "/".join(parts)


def guess_ext_from_content_type(ct):
    ct = (ct or "").split(";")[0].strip().lower()
    table = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
        "image/x-icon": ".ico",
        "image/vnd.microsoft.icon": ".ico",
        "text/css": ".css",
        "text/html": ".html",
        "application/javascript": ".js",
        "text/javascript": ".js",
        "application/json": ".json",
        "font/woff": ".woff",
        "font/woff2": ".woff2",
        "font/ttf": ".ttf",
        "application/font-woff": ".woff",
        "video/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "application/pdf": ".pdf",
        "text/xml": ".xml",
        "application/xml": ".xml",
    }
    return table.get(ct, "")
