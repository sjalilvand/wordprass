# -*- coding: utf-8 -*-
"""دانلود فایل‌های رسانه‌ای (عکس، ویدیو، سند...) از خروجی REST API رسانه‌ها"""
import os
import time
from urllib.parse import urlparse

import requests

from .utils import (
    log,
    sanitize_filename,
    guess_ext_from_content_type,
    human_size,
    polite_sleep,
)

MAX_FILE_MB = 120


def _unique_path(directory, filename, used):
    """ساخت مسیر یکتا برای جلوگیری از بازنویسی فایل هم‌نام"""
    base, ext = os.path.splitext(filename)
    if not base:
        base = "file"
    candidate = base + ext
    n = 2
    key = candidate.lower()
    while (key in used) or os.path.exists(os.path.join(directory, candidate)):
        if key in used:  # فقط وقتی در این اجرا دیده شده شماره بگذار
            candidate = f"{base}-{n}{ext}"
            key = candidate.lower()
            n += 1
        else:
            break
    used.add(candidate.lower())
    return candidate


def download_media(session, media_items, media_dir, delay=0.35, progress_cb=None):
    """
    دانلود همه فایل‌های source_url از لیست media.
    خروجی: (dict نگاشت url->نام فایل, تعداد موفق, حجم کل)
    """
    os.makedirs(media_dir, exist_ok=True)
    used = set()
    mapping = {}
    ok_count = 0
    total_bytes = 0
    failed = 0

    items = [m for m in (media_items or []) if isinstance(m, dict)]
    for i, m in enumerate(items, 1):
        url = m.get("source_url") or ""
        if not url:
            continue
        if url in mapping:
            continue
        if progress_cb:
            progress_cb(int(i * 100 / max(1, len(items))),
                        f"دانلود رسانه {i} از {len(items)}")
        path_part = urlparse(url).path
        fname = os.path.basename(path_part)
        if not fname:
            fname = "file"
        fname = sanitize_filename(fname)
        if "." not in fname:
            fname += guess_ext_from_content_type(m.get("mime_type") or "")
        try:
            r = session.get(url, stream=True, timeout=120)
        except requests.RequestException as e:
            log.debug("  خطای دانلود %s : %s", url, e)
            failed += 1
            polite_sleep(delay)
            continue
        if r.status_code != 200:
            log.debug("  پاسخ %s برای %s", r.status_code, url)
            failed += 1
            polite_sleep(delay)
            continue
        fname = _unique_path(media_dir, fname, used)
        dest = os.path.join(media_dir, fname)
        size = 0
        limit_bytes = MAX_FILE_MB * 1024 * 1024
        try:
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=256 * 1024):
                    if not chunk:
                        continue
                    size += len(chunk)
                    if size > limit_bytes:
                        raise IOError("فایل از حد مجاز بزرگ‌تر است")
                    f.write(chunk)
            ok_count += 1
            total_bytes += size
            mapping[url] = fname
        except (IOError, OSError) as e:
            log.debug("  ذخیره ناموفق %s : %s", url, e)
            failed += 1
            try:
                os.remove(dest)
            except OSError:
                pass
        polite_sleep(delay)

    log.info("[OK] رسانه‌ها: %s فایل دانلود شد (%s)؛ ناموفق: %s",
             ok_count, human_size(total_bytes), failed)
    return mapping, ok_count, total_bytes
