# -*- coding: utf-8 -*-
"""تشخیص وردپرس بودن سایت و یافتن ریشه REST API"""
import re

import requests

from .utils import log


def detect_wordpress(session, base_url):
    """تشخیص وردپرس؛ خروجی: dict با is_wp / api_root / اطلاعات سایت"""
    info = {
        "base_url": base_url.rstrip("/"),
        "is_wp": False,
        "api_root": None,
        "site": {},
        "wp_version": None,
        "theme": None,
        "namespaces": [],
    }

    candidates = [
        base_url.rstrip("/") + "/wp-json/",
        base_url.rstrip("/") + "/?rest_route=/",
    ]

    for api in candidates:
        try:
            r = session.get(api, timeout=45)
        except requests.RequestException as e:
            log.debug("probe %s failed: %s", api, e)
            continue
        if r.status_code != 200:
            continue
        try:
            data = r.json()
        except ValueError:
            continue
        if isinstance(data, dict) and "namespaces" in data:
            info["is_wp"] = True
            info["api_root"] = api if api.endswith("/") else api + "/"
            info["namespaces"] = data.get("namespaces", [])
            site = {}
            for k in ("name", "description", "url", "home", "timezone_string",
                      "gmt_offset", "site_icon_url", "site_logo", "site_icon"):
                if data.get(k):
                    site[k] = data.get(k)
            info["site"] = site
            break

    # بررسی HTML صفحه اصلی برای نسخه، قالب و تأیید وردپرس بودن
    try:
        r = session.get(base_url + "/", timeout=45)
        html = r.text[:300000]
        m = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']'
                      r'WordPress\s*([0-9.]+)', html, re.I)
        if not m:
            m = re.search(r'content=["\']WordPress\s*([0-9.]+)["\']', html, re.I)
        if m:
            info["wp_version"] = m.group(1)
        m = re.search(r'wp-content/themes/([a-z0-9_\-]+)/', html, re.I)
        if m:
            info["theme"] = m.group(1)
        if not info["is_wp"] and re.search(r"(wp-content|wp-includes)", html):
            info["is_wp"] = True
            info["api_root"] = base_url.rstrip("/") + "/wp-json/"
    except requests.RequestException:
        pass

    return info
