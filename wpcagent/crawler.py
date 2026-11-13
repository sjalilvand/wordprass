# -*- coding: utf-8 -*-
"""
خزنده آینه استاتیک: دریافت کامل صفحات HTML، CSS، JS، تصاویر و فونت‌های
هم‌دامنه و بازنویسی لینک‌ها به مسیر نسبی تا سایت به‌صورت آفلاین عین همان
سایت اصلی باز شود.
"""
import os
import posixpath
import re
import time
from collections import deque
from urllib.parse import urljoin, urldefrag, urlparse, unquote

import requests
from bs4 import BeautifulSoup

from .utils import (
    host_key,
    log,
    safe_relpath,
    sanitize_filename,
    human_size,
    polite_sleep,
)

CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)([^'\")]+)\1\s*\)", re.I)
CSS_IMPORT_RE = re.compile(r"@import\s+(?:url\()?\s*(['\"])([^'\"]+)\1", re.I)

SKIP_PATH_RE = re.compile(
    r"(wp-login\.php|wp-admin|wp-json|xmlrpc\.php|/feed/?$|"
    r"/wp-cron\.php|/wp-mail\.php|/comments/feed|replytocom=|"
    r"/wp-signup\.php|/wp-register\.php)", re.I)

ASSET_SKIP_EXT = (".zip", ".exe", ".dmg", ".rar", ".7z", ".msi", ".deb")


def canon_url(url):
    """کلید یکتای URL: بدون فرگمنت، بدون www، دکود مسیر"""
    url, _frag = urldefrag(url)
    p = urlparse(url)
    host = (p.netloc or "").lower().removeprefix("www.")
    path = unquote(p.path or "/")
    if path == "":
        path = "/"
    return (host, path, p.query)


def rel_between(src_rel, dst_rel):
    """مسیر نسبی از فایل مبدأ به فایل مقصد با اسلش یونیکسی"""
    src_dir = posixpath.dirname(src_rel)
    rel = posixpath.relpath(dst_rel, src_dir or ".")
    if not rel.startswith("."):
        rel = "./" + rel
    return rel


class MirrorCrawler:
    def __init__(self, session, base_url, out_dir,
                 max_pages=300, max_assets=1500, delay=0.35,
                 max_asset_mb=80, progress_cb=None):
        self.session = session
        self.base = base_url.rstrip("/") + "/"
        self.base_host = host_key(self.base)
        self.out_dir = out_dir
        self.max_pages = max_pages
        self.max_assets = max_assets
        self.delay = delay
        self.max_asset_mb = max_asset_mb
        self.progress_cb = progress_cb

        self.page_queue = deque([self.base])
        self.asset_queue = deque()
        self.pages = {}     # key -> {"url", "raw", "rel"}
        self.assets = {}    # key -> {"url", "rel", "bytes"}
        self.css_files = {} # key -> {"url", "raw", "rel"}
        self.failed_pages = 0
        self.failed_assets = 0
        self.external_refs = set()
        self.total_bytes = 0
        self.stop = False

    # ---------- مسیر ذخیره ----------
    def page_rel(self, url):
        """مسیر نسبی ذخیره صفحه HTML"""
        p = urlparse(url)
        path = unquote(p.path or "/")
        if p.query:
            q = sanitize_filename(re.sub(r"[^A-Za-z0-9._-]+", "_", p.query), 60)
            if path.endswith("/"):
                path += "index__" + q + ".html"
            else:
                base, ext = posixpath.splitext(path)
                path = base + "__" + q + (ext or ".html")
        if path.endswith("/"):
            rel = safe_relpath(path)
            return (rel + "/index.html") if rel else "index.html"
        ext = posixpath.splitext(path)[1].lower()
        if ext in ("", ".php", ".htm"):
            rel = safe_relpath(path)
            return (rel + "/index.html") if rel else "index.html"
        rel = safe_relpath(path)
        return rel if rel else "index.html"

    def asset_rel(self, url):
        """مسیر نسبی ذخیره asset — ساختار پوشه‌ها مثل سایت اصلی حفظ می‌شود"""
        p = urlparse(url)
        path = unquote(p.path or "/")
        rel = safe_relpath(path)
        if not rel:
            rel = "assets/unnamed"
        if p.query:
            q = sanitize_filename(re.sub(r"[^A-Za-z0-9._-]+", "_", p.query), 40)
            root, ext = posixpath.splitext(rel)
            rel = (root or "assets/file") + "__" + q + (ext or "")
        return rel

    def same_site(self, url):
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return False
        return host_key(url) == self.base_host

    # ---------- دریافت ----------
    def _get(self, url):
        try:
            r = self.session.get(url, timeout=60)
            return r
        except requests.RequestException as e:
            log.debug("  خطای دریافت %s : %s", url, e)
            return None

    def crawl(self):
        """فاز ۱: دریافت صفحات HTML؛ فاز ۲: دریافت asset ها؛ فاز ۳: بازنویسی"""
        self._crawl_pages()
        self._crawl_assets()
        self._rewrite_css()
        self._rewrite_pages()
        self._write_files()
        return self._summary()

    # فاز ۱
    def _crawl_pages(self):
        seen = set()
        while self.page_queue and len(self.pages) < self.max_pages and not self.stop:
            url = self.page_queue.popleft()
            key = canon_url(url)
            if key in seen:
                continue
            seen.add(key)
            if SKIP_PATH_RE.search(urlparse(url).path or ""):
                continue
            if self.progress_cb:
                self.progress_cb(30 + int(len(self.pages) * 20 / max(1, self.max_pages)),
                                 f"دریافت صفحه {len(self.pages) + 1}")
            r = self._get(url)
            polite_sleep(self.delay)
            if r is None or r.status_code != 200:
                self.failed_pages += 1
                continue
            ctype = (r.headers.get("Content-Type") or "").lower()
            if "html" not in ctype:
                # صفحه اصلی که HTML نیست؛ به‌صورت asset ذخیره شود
                if self.same_site(url) and len(self.assets) < self.max_assets:
                    self.asset_queue.append(url)
                continue
            self.pages[key] = {"url": r.url, "raw": r.text, "rel": self.page_rel(r.url)}
            self._collect_links(r.url, r.text)

        log.info("[OK] آینه: %s صفحه HTML دریافت شد (ناموفق: %s)",
                 len(self.pages), self.failed_pages)

    def _collect_links(self, page_url, html):
        soup = BeautifulSoup(html, "lxml")
        base_tag = soup.find("base", href=True)
        base_for_join = base_tag["href"] if base_tag else page_url

        # صفحات داخلی
        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            full = urljoin(base_for_join, href)
            if self.same_site(full):
                parsed = urlparse(full)
                if not parsed.path and not parsed.query:
                    continue
                if parsed.query and ("p=" in parsed.query or "page_id=" in parsed.query):
                    # شورت‌لینک‌های تکراری؛ فقط اگر قبلاً دیده نشده باشند از صفحه اصلی رد می‌شوند
                    pass
                if not SKIP_PATH_RE.search(parsed.path or ""):
                    self.page_queue.append(full)
            else:
                self.external_refs.add(full)

        # asset ها
        for url in self._asset_urls(soup, page_url):
            if self.same_site(url):
                if canon_url(url) not in self.assets and len(self.assets) < self.max_assets:
                    self.asset_queue.append(url)
            else:
                self.external_refs.add(url)

    def _asset_urls(self, soup, page_url):
        """استخراج همه URL های asset از یک صفحه"""
        urls = []
        def add(ref):
            if not ref:
                return
            ref = ref.strip()
            if ref.startswith(("data:", "#", "javascript:", "mailto:")):
                return
            urls.append(urljoin(page_url, ref))

        for tag in soup.find_all(["link"]):
            rels = (tag.get("rel") or [])
            rels = [str(x).lower() for x in rels]
            if tag.get("href") and (
                "stylesheet" in rels or "icon" in rels or "shortcut" in rels
                or "apple-touch-icon" in rels or "preload" in rels or "manifest" in rels
            ):
                add(tag["href"])
        for tag in soup.find_all("script", src=True):
            add(tag["src"])
        for tag in soup.find_all("img"):
            if tag.get("src"):
                add(tag["src"])
            if tag.get("data-src"):
                add(tag["data-src"])
            if tag.get("data-srcset") or tag.get("srcset"):
                for u, _s in self._parse_srcset(tag.get("srcset") or tag.get("data-srcset")):
                    add(u)
        for tag in soup.find_all(["source", "video", "audio", "embed", "track"]):
            if tag.get("src"):
                add(tag["src"])
            if tag.get("poster"):
                add(tag["poster"])
        for tag in soup.find_all("iframe", src=True):
            add(tag["src"])
        for tag in soup.find_all("meta"):
            if str(tag.get("property") or tag.get("name") or "").lower() in (
                "og:image", "twitter:image", "og:image:secure_url"
            ) and tag.get("content"):
                add(tag["content"])
        # url(...) داخل استایل‌های خطی و تگ‌های style
        for tag in soup.find_all(style=True):
            for _q, u in CSS_URL_RE.findall(tag["style"]):
                add(u)
        for style_tag in soup.find_all("style"):
            for _q, u in CSS_URL_RE.findall(style_tag.get_text() or ""):
                add(u)
        return urls

    @staticmethod
    def _parse_srcset(srcset):
        out = []
        for part in (srcset or "").split(","):
            part = part.strip()
            if not part:
                continue
            bits = part.split()
            if bits:
                out.append((bits[0], bits[1] if len(bits) > 1 else ""))
        return out

    # فاز ۲
    def _crawl_assets(self):
        seen = set()
        limit_bytes = self.max_asset_mb * 1024 * 1024
        n_total = 0
        while self.asset_queue and len(self.assets) < self.max_assets and not self.stop:
            url = self.asset_queue.popleft()
            key = canon_url(url)
            if key in seen or key in self.assets:
                continue
            seen.add(key)
            if urlparse(url).path.lower().endswith(ASSET_SKIP_EXT):
                continue
            if self.progress_cb:
                self.progress_cb(50 + int(len(self.assets) * 10 / max(1, self.max_assets)),
                                 f"دریافت فایل {len(self.assets) + 1}")
            r = self._get(url)
            polite_sleep(self.delay)
            if r is None or r.status_code != 200:
                self.failed_assets += 1
                continue
            ctype = (r.headers.get("Content-Type") or "").lower()
            is_css = "text/css" in ctype or url.lower().endswith(".css")
            size = len(r.content or b"")
            if size > limit_bytes:
                log.debug("  ردشد (بزرگ): %s", url)
                self.failed_assets += 1
                continue
            if is_css:
                self.css_files[key] = {"url": r.url, "raw": r.text, "rel": self.asset_rel(r.url)}
                self.assets[key] = {"url": r.url, "rel": self.asset_rel(r.url), "bytes": size}
            else:
                self.assets[key] = {"url": r.url, "rel": self.asset_rel(r.url),
                                    "bytes": size, "content": r.content}
            self.total_bytes += size
            n_total += 1
            # asset های داخل CSS (فونت و تصاویر)
            if is_css:
                for ref in self._css_asset_urls(r.text, r.url):
                    if self.same_site(ref) and len(self.assets) < self.max_assets:
                        self.asset_queue.append(ref)
                    elif not self.same_site(ref):
                        self.external_refs.add(ref)
        log.info("[OK] آینه: %s فایل CSS/JS/تصویر/فونت دریافت شد (%s؛ ناموفق: %s)",
                 n_total, human_size(self.total_bytes), self.failed_assets)

    def _css_asset_urls(self, css_text, css_url):
        refs = []
        for _q, u in CSS_URL_RE.findall(css_text or ""):
            if u.startswith("data:"):
                continue
            refs.append(urljoin(css_url, u))
        for _q, u in CSS_IMPORT_RE.findall(css_text or ""):
            refs.append(urljoin(css_url, u))
        return refs

    # فاز ۳: بازنویسی CSS
    def _rewrite_css(self):
        for key, item in self.css_files.items():
            text = item["raw"]
            def repl(match):
                q, u = match.group(1), match.group(2)
                if u.startswith(("data:", "#")):
                    return match.group(0)
                target_key = canon_url(urljoin(item["url"], u))
                if target_key in self.assets:
                    rel = rel_between(item["rel"], self.assets[target_key]["rel"])
                    return f"url({q}{rel}{q})"
                if not self.same_site(urljoin(item["url"], u)):
                    return match.group(0)
                return f"url({q}{u}{q})"
            text = CSS_URL_RE.sub(repl, text)
            text = CSS_IMPORT_RE.sub(
                lambda m: f"@import url('{m.group(2)}')" if not self.same_site(
                    urljoin(item["url"], m.group(2)))
                else f"@import url('{m.group(2)}')",
                text,
            )
            item["out"] = text

    # فاز ۳: بازنویسی HTML
    def _rewrite_pages(self):
        for key, page in self.pages.items():
            soup = BeautifulSoup(page["raw"], "lxml")
            page_url = page["url"]

            def map_ref(ref):
                """URL مطلق یا نسبی → مسیر محلی نسبی یا همان URL"""
                if not ref:
                    return ref
                ref = ref.strip()
                if ref.startswith(("data:", "#", "javascript:", "mailto:", "tel:")):
                    return ref
                full = urljoin(page_url, ref)
                tk = canon_url(full)
                if tk in self.pages:
                    return rel_between(page["rel"], self.pages[tk]["rel"])
                if tk in self.assets:
                    return rel_between(page["rel"], self.assets[tk]["rel"])
                return full if not self.same_site(full) else full

            for tag in soup.find_all("a", href=True):
                tag["href"] = map_ref(tag["href"])
            for tag in soup.find_all("img"):
                if tag.get("src"):
                    tag["src"] = map_ref(tag["src"])
                if tag.get("data-src"):
                    tag["data-src"] = map_ref(tag["data-src"])
                ss = tag.get("srcset") or tag.get("data-srcset")
                if ss:
                    parts = []
                    for u, size in self._parse_srcset(ss):
                        parts.append(map_ref(u) + ((" " + size) if size else ""))
                    val = ", ".join(parts)
                    if tag.get("srcset"):
                        tag["srcset"] = val
                    if tag.get("data-srcset"):
                        tag["data-srcset"] = val
            for tag in soup.find_all(["source", "video", "audio", "embed", "track"]):
                if tag.get("src"):
                    tag["src"] = map_ref(tag["src"])
                if tag.get("poster"):
                    tag["poster"] = map_ref(tag["poster"])
            for tag in soup.find_all("iframe", src=True):
                tag["src"] = map_ref(tag["src"])
            for tag in soup.find_all("link", href=True):
                rels = [str(x).lower() for x in (tag.get("rel") or [])]
                if any(x in rels for x in ("stylesheet", "icon", "shortcut",
                                           "apple-touch-icon", "preload", "manifest")):
                    tag["href"] = map_ref(tag["href"])
            for tag in soup.find_all("script", src=True):
                tag["src"] = map_ref(tag["src"])
            for tag in soup.find_all("meta"):
                if str(tag.get("property") or tag.get("name") or "").lower() in (
                    "og:image", "twitter:image", "og:image:secure_url"
                ) and tag.get("content"):
                    tag["content"] = map_ref(tag["content"])
            # استایل خطی و بلوک style
            for tag in soup.find_all(style=True):
                tag["style"] = self._rewrite_inline_css(tag["style"], page_url, page["rel"])
            for st in soup.find_all("style"):
                css = st.get_text() or ""
                st.string = self._rewrite_inline_css(css, page_url, page["rel"])

            page["out"] = str(soup)

    def _rewrite_inline_css(self, css, page_url, page_rel):
        def repl(match):
            q, u = match.group(1), match.group(2)
            if u.startswith(("data:", "#")):
                return match.group(0)
            tk = canon_url(urljoin(page_url, u))
            if tk in self.assets:
                return f"url({q}{rel_between(page_rel, self.assets[tk]['rel'])}{q})"
            return match.group(0)
        return CSS_URL_RE.sub(repl, css or "")

    # فاز ۴: نوشتن فایل‌ها
    def _write_files(self):
        os.makedirs(self.out_dir, exist_ok=True)
        for item in self.pages.values():
            self._write(os.path.join(self.out_dir, item["rel"]), item.get("out", item["raw"]))
        for item in self.assets.values():
            if "content" in item and item["content"] is not None:
                self._write(os.path.join(self.out_dir, item["rel"]), item["content"], binary=True)
        for item in self.css_files.values():
            self._write(os.path.join(self.out_dir, item["rel"]),
                        item.get("out", item["raw"]))

    @staticmethod
    def _write(path, data, binary=False):
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        mode = "wb" if binary else "w"
        try:
            with open(path, mode, **({} if binary else {"encoding": "utf-8"})) as f:
                f.write(data)
        except (IOError, OSError) as e:
            log.debug("  خطای نوشتن %s : %s", path, e)

    def _summary(self):
        return {
            "pages": len(self.pages),
            "assets": len(self.assets),
            "failed_pages": self.failed_pages,
            "failed_assets": self.failed_assets,
            "bytes": self.total_bytes,
            "external_refs": len(self.external_refs),
        }


def crawl_mirror(session, base_url, out_dir, max_pages=300, max_assets=1500,
                 delay=0.35, max_asset_mb=80, progress_cb=None):
    """نقطه ورود ماژول آینه"""
    crawler = MirrorCrawler(
        session, base_url, out_dir,
        max_pages=max_pages, max_assets=max_assets, delay=delay,
        max_asset_mb=max_asset_mb, progress_cb=progress_cb,
    )
    return crawler.crawl()
