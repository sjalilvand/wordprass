# -*- coding: utf-8 -*-
"""دریافت محتوا از REST API وردپرس (نوشته، برگه، رسانه، دیدگاه، منو، تکسونومی...)"""
import json
import os
import time

import requests

from .utils import log

# نقاط پایانی هسته وردپرس: (کلید ذخیره، rest_base)
CORE_ENDPOINTS = [
    ("posts", "posts"),
    ("pages", "pages"),
    ("media", "media"),
    ("categories", "categories"),
    ("tags", "tags"),
    ("comments", "comments"),
    ("users", "users"),
    ("menus", "menus"),
    ("menu_items", "menu-items"),
]

PAGE_SIZE = 100


def fetch_endpoint(session, api_root, rest_base, limit=None, delay=0.3):
    """دریافت همه آیتم‌های یک endpoint با صفحه‌بندی خودکار"""
    url = api_root.rstrip("/") + "/wp/v2/" + rest_base
    items = []
    page = 1
    while True:
        try:
            r = session.get(
                url,
                params={"per_page": PAGE_SIZE, "page": page, "orderby": "id", "order": "asc"},
                timeout=90,
            )
        except requests.RequestException as e:
            log.debug("  خطای شبکه در %s صفحه %s: %s", rest_base, page, e)
            break
        if r.status_code in (401, 403, 404):
            # endpoint عمومی نیست یا وجود ندارد
            return None if not items else items
        if r.status_code == 400:
            # فراتر رفتن از آخرین صفحه
            break
        r.raise_for_status()
        try:
            data = r.json()
        except ValueError:
            break
        if not isinstance(data, list):
            return data  # endpoint دیکشنری‌محور مثل types
        items.extend(data)
        try:
            total_pages = int(r.headers.get("X-WP-TotalPages", "1") or "1")
        except ValueError:
            total_pages = 1
        if limit and len(items) >= limit:
            return items[:limit]
        if page >= total_pages:
            break
        page += 1
        if delay:
            time.sleep(delay)
    return items


def discover_custom_post_types(session, api_root, delay=0.3):
    """کشف انواع محتوای سفارشی از endpoint مربوط به types"""
    try:
        r = session.get(api_root.rstrip("/") + "/wp/v2/types", timeout=60)
        if r.status_code != 200:
            return {}
        types = r.json()
    except (requests.RequestException, ValueError):
        return {}
    result = {}
    for name, t in (types or {}).items():
        if name in ("post", "page", "attachment"):
            continue
        if not t.get("show_in_rest"):
            continue
        rest_base = t.get("rest_base")
        if rest_base:
            result[name] = {
                "rest_base": rest_base,
                "name": t.get("name", name),
                "slug": t.get("slug", name),
            }
    return result


def discover_custom_taxonomies(session, api_root):
    """کشف تکسونومی‌های سفارشی"""
    try:
        r = session.get(api_root.rstrip("/") + "/wp/v2/taxonomies", timeout=60)
        if r.status_code != 200:
            return {}
        taxes = r.json()
    except (requests.RequestException, ValueError):
        return {}
    result = {}
    for name, t in (taxes or {}).items():
        if name in ("category", "post_tag", "nav_menu", "link_category", "post_format"):
            continue
        if not t.get("show_in_rest"):
            continue
        rest_base = t.get("rest_base")
        if rest_base:
            result[name] = {
                "rest_base": rest_base,
                "name": t.get("name", name),
                "slug": t.get("slug", name),
            }
    return result


def scrape_site(session, site_info, out_dir, limit=None, delay=0.3):
    """
    دریافت کل محتوای ساختاریافته سایت وردپرسی.
    خروجی: (data dict, counts dict)
    """
    api_root = site_info["api_root"]
    data = {}
    counts = {}
    api_dir = os.path.join(out_dir, "api_data")
    os.makedirs(api_dir, exist_ok=True)

    if not api_root:
        log.info("[!] REST API وردپرس در دسترس نیست؛ دریافت ساختاری رد شد")
        return data, counts

    log.info("[..] دریافت محتوا از REST API: %s", api_root)

    for key, rest_base in CORE_ENDPOINTS:
        items = fetch_endpoint(session, api_root, rest_base, limit=limit, delay=delay)
        if items is None:
            log.debug("  endpoint %s در دسترس نیست", rest_base)
            data[key] = []
            continue
        data[key] = items
        counts[key] = len(items)
        try:
            with open(os.path.join(api_dir, key + ".json"), "w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=1)
        except OSError as e:
            log.debug("  ذخیره %s.json ناموفق: %s", key, e)
        if items:
            log.info("[OK] %-12s : %s آیتم", key, len(items))
        else:
            log.debug("  %-12s : خالی", key)

    # انواع محتوای سفارشی
    cpt = discover_custom_post_types(session, api_root)
    data["custom_types"] = {}
    for name, meta in cpt.items():
        items = fetch_endpoint(session, api_root, meta["rest_base"], limit=limit, delay=delay)
        if items:
            data["custom_types"][name] = {"meta": meta, "items": items}
            counts["cpt_" + name] = len(items)
            log.info("[OK] نوع سفارشی %-16s : %s آیتم", name, len(items))
            try:
                with open(os.path.join(api_dir, "cpt_" + name + ".json"), "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=1)
            except OSError:
                pass

    # تکسونومی‌های سفارشی
    taxes = discover_custom_taxonomies(session, api_root)
    data["custom_taxonomies"] = {}
    for name, meta in taxes.items():
        items = fetch_endpoint(session, api_root, meta["rest_base"], limit=limit, delay=delay)
        if items:
            data["custom_taxonomies"][name] = {"meta": meta, "terms": items}
            counts["tax_" + name] = len(items)
            log.info("[OK] تکسونومی %-16s : %s ترم", name, len(items))
            try:
                with open(os.path.join(api_dir, "tax_" + name + ".json"), "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=1)
            except OSError:
                pass

    return data, counts
