# -*- coding: utf-8 -*-
"""
سایت‌ساز پویا: از خروجی کلون یک سایت Flask کامل با دیتابیس می‌سازد
Dynamic site builder: turns a clone output folder into a full Flask site.
"""
import base64
import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from urllib.parse import urlparse

from .utils import log

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site_template")


class BuildError(Exception):
    pass


def _wp_rendered(value):
    """برداشت متن از فیلدهای rendered وردپرس"""
    if isinstance(value, dict):
        value = value.get("rendered", "")
    return re.sub(r"<[^>]+>", " ", value or "").strip()


def _clean_date(value):
    if not value:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    return str(value)[:16].replace("T", " ")


def _strip_wp_shortcode(text):
    text = re.sub(r"\[/?[^\]]{1,40}\]", "", text or "")
    return text


def _build_media_map(api_dir, media_dir):
    """نگاشت URL رسانه وردپرس به نام فایل محلی"""
    media_map = {}
    media_json = os.path.join(api_dir, "media.json")
    local_files = []
    if os.path.isdir(media_dir):
        local_files = sorted(os.listdir(media_dir))
    items = []
    if os.path.exists(media_json):
        try:
            with open(media_json, encoding="utf-8") as f:
                items = json.load(f)
        except (ValueError, OSError):
            items = []
    for m in items:
        if not isinstance(m, dict):
            continue
        url = m.get("source_url") or ""
        if not url:
            continue
        base = url.rsplit("/", 1)[-1].split("?")[0].split("#")[0]
        local = None
        if base and base in local_files:
            local = base
        else:
            root, dot, ext = base.partition(".")
            for fname in local_files:
                if dot and fname.startswith(root + "-") and fname.endswith(ext):
                    local = fname
                    break
        if local:
            media_map[url] = local
            media_map["basename:" + base] = local
    return media_map


def _copy_media(media_dir, project_dir, progress_cb=None):
    uploads = os.path.join(project_dir, "static", "uploads")
    os.makedirs(uploads, exist_ok=True)
    copied = 0
    if os.path.isdir(media_dir):
        for fname in os.listdir(media_dir):
            src = os.path.join(media_dir, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(uploads, fname))
                copied += 1
                if progress_cb and copied % 25 == 0:
                    progress_cb(-1, "build:media")
    return copied


def _seed_database(project_dir, api_dir, cfg, media_map, progress_cb=None):
    db_path = os.path.join(project_dir, "database.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    schema = open(os.path.join(TEMPLATE_DIR, "schema.sql"), encoding="utf-8").read()
    cur.executescript(schema)

    def load(name):
        path = os.path.join(api_dir, name + ".json")
        if not os.path.exists(path):
            return []
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (ValueError, OSError):
            return []

    counts = {"posts": 0, "pages": 0, "terms": 0, "comments": 0, "menu_items": 0}

    # --- دسته‌ها و برچسب‌ها
    wp_term_slug_to_id = {}
    for kind, items in (("category", load("categories")), ("tag", load("tags"))):
        for it in items:
            name = _wp_rendered(it.get("name")) or it.get("slug") or kind
            slug = it.get("slug") or name
            try:
                cur.execute("INSERT INTO terms(ttype, name, slug) VALUES(?,?,?)", (kind, name, slug))
                tid = cur.lastrowid
            except sqlite3.IntegrityError:
                row = cur.execute("SELECT id FROM terms WHERE slug=?", (slug,)).fetchone()
                tid = row[0] if row else None
            if tid:
                wp_term_slug_to_id[it.get("id")] = tid
                counts["terms"] += 1
    counts["terms"] = cur.execute("SELECT COUNT(*) FROM terms").fetchone()[0]

    # --- نوشته‌ها و برگه‌ها
    def insert_content(kind, items):
        inserted = []
        for it in items:
            title = _wp_rendered(it.get("title")) or "بدون عنوان"
            slug = it.get("slug") or re.sub(r"\s+", "-", title.lower())[:70]
            content = _strip_wp_shortcode(it.get("content", {}).get("rendered", "") if isinstance(it.get("content"), dict) else it.get("content", ""))
            excerpt_raw = it.get("excerpt", {})
            excerpt = _wp_rendered(excerpt_raw.get("rendered", "") if isinstance(excerpt_raw, dict) else excerpt_raw)[:300]
            # تصویر شاخص
            image = ""
            fm = it.get("featured_media")
            if fm and fm in media_by_id:
                image = media_by_id[fm]
            try:
                cur.execute(
                    "INSERT INTO content(ctype, title, slug, content, excerpt, status, image, created_at) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (kind, title, slug, content, excerpt,
                     "publish" if it.get("status", "publish") == "publish" else it.get("status", "publish"),
                     image, _clean_date(it.get("date_gmt") or it.get("date"))))
                new_id = cur.lastrowid
            except sqlite3.IntegrityError:
                slug2 = f"{slug}-{secrets.token_hex(3)}"
                cur.execute(
                    "INSERT INTO content(ctype, title, slug, content, excerpt, status, image, created_at) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (kind, title, slug2, content, excerpt, it.get("status", "publish"),
                     image, _clean_date(it.get("date_gmt") or it.get("date"))))
                new_id = cur.lastrowid
            # ارتباط دسته/برچسب
            term_ids = list(it.get("categories") or []) + list(it.get("tags") or [])
            for wp_tid in term_ids:
                local_tid = wp_term_slug_to_id.get(wp_tid)
                if local_tid:
                    try:
                        cur.execute("INSERT INTO content_terms(content_id, term_id) VALUES(?,?)", (new_id, local_tid))
                    except sqlite3.IntegrityError:
                        pass
            inserted.append((it.get("id"), new_id))
        return inserted

    media_by_id = {}
    for m in load("media"):
        if isinstance(m, dict) and m.get("id"):
            url = m.get("source_url") or ""
            local = media_map.get(url)
            if local:
                media_by_id[m["id"]] = local

    wp_post_map = {}
    for wp_id, new_id in insert_content("post", load("posts")):
        wp_post_map[wp_id] = new_id
        counts["posts"] += 1
    for wp_id, new_id in insert_content("page", load("pages")):
        wp_post_map[wp_id] = new_id
        counts["pages"] += 1

    # --- دیدگاه‌ها
    for cm in load("comments"):
        local_post = wp_post_map.get(cm.get("post"))
        if not local_post:
            continue
        body = _wp_rendered(cm.get("content"))[:2000]
        if not body:
            continue
        cur.execute(
            "INSERT INTO comments(content_id, author, email, body, created_at, approved) VALUES(?,?,?,?,?,1)",
            (local_post, cm.get("author_name") or "مهمان", "", body, _clean_date(cm.get("date"))))
        counts["comments"] += 1

    # --- منو: از آیتم‌های منوی وردپرس، در نبود آن از برگه‌ها
    menu_items = load("menu_items")
    position = 0
    if menu_items:
        for mi in menu_items:
            title = _wp_rendered(mi.get("title")) or "منو"
            url = mi.get("url") or ""
            if not url:
                continue
            cur.execute("INSERT INTO menu_items(title, url, position) VALUES(?,?,?)",
                        (title, url, position))
            position += 1
            counts["menu_items"] += 1
    if position == 0:
        cur.execute("INSERT INTO menu_items(title, url, position) VALUES(?,?,?)", ("Blog", "/blog", 0))
        pages_menu = cur.execute(
            "SELECT title, slug FROM content WHERE ctype='page' AND status='publish' ORDER BY menu_order LIMIT 5"
        ).fetchall()
        for t, s in pages_menu:
            position += 1
            cur.execute("INSERT INTO menu_items(title, url, position) VALUES(?,?,?)", (t, f"/page/{s}", position))
        counts["menu_items"] = position + 1

    # --- تنظیمات اولیه
    cur.execute("INSERT OR REPLACE INTO settings(k, v) VALUES('site_name', ?)", (cfg.get("site_name"),))
    cur.execute("INSERT OR REPLACE INTO settings(k, v) VALUES('tagline', ?)", (cfg.get("tagline", ""),))
    cur.execute("INSERT OR REPLACE INTO settings(k, v) VALUES('theme_color', ?)", (cfg.get("theme_color", "#4f46e5"),))
    conn.commit()
    conn.close()

    info = {
        "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
        "source": cfg.get("source_url", ""),
        "languages": cfg.get("languages", ["fa"]),
        "counts": counts,
        "media_files": len(media_map),
    }
    with open(os.path.join(project_dir, "build-info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    return counts


def _run_git(args, cwd, env=None):
    proc = subprocess.run(
        ["git"] + args, cwd=cwd, env=env,
        capture_output=True, text=True, timeout=180,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def git_publish(project_dir, repo_url, token, progress_cb=None):
    """ساخت مخزن گیت و ارسال (push) به آدرس داده‌شده — توکن در هیچ فایلی ذخیره نمی‌شود"""
    token = (token or "").strip()
    repo_url = (repo_url or "").strip()
    if not repo_url:
        return False, "no_repo"
    if "://" not in repo_url:
        # مسیر سیستم‌عامل محلی (برای تست/مخزن محلی) را دست‌نخورده نگه می‌داریم
        is_fs_path = repo_url.startswith(("/", "./", "../", "~", os.sep)) or ":\\" in repo_url
        if not is_fs_path:
            repo_url = "https://" + repo_url
    clean_url = repo_url
    if token:
        # توکن فقط در URL لحظه‌ای دستور push استفاده می‌شود
        push_url = repo_url.replace("https://", f"https://{token}@")
        push_url = push_url.replace("http://", f"http://{token}@")
    else:
        push_url = repo_url

    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"

    if progress_cb:
        progress_cb(80, "build:git")
    code, out = _run_git(["init"], project_dir, env)
    if code != 0 and "already exists" not in out:
        return False, _safe(out, token)
    _run_git(["config", "user.name", "WordPress Clone Agent"], project_dir, env)
    _run_git(["config", "user.email", "agent@local"], project_dir, env)
    code, out = _run_git(["add", "-A"], project_dir, env)
    if code != 0:
        return False, _safe(out, token)
    code, out = _run_git(["commit", "-m", "Dynamic site built by WordPress Clone Agent"], project_dir, env)
    if code != 0 and "nothing to commit" not in out:
        return False, _safe(out, token)
    code, out = _run_git(["branch", "-M", "main"], project_dir, env)
    _run_git(["remote", "remove", "origin"], project_dir, env)
    code, out = _run_git(["remote", "add", "origin", clean_url], project_dir, env)
    if code != 0:
        return False, _safe(out, token)
    if progress_cb:
        progress_cb(88, "build:git_push")
    # push با URL لحظه‌ای (توکن فقط همین‌جا و فقط در حافظه پردازه استفاده می‌شود)
    code, out = _run_git(["push", push_url, "main"], project_dir, env)
    if code != 0:
        return False, _safe(out, token)
    return True, "pushed"


def _safe(message, token):
    """حذف توکن از هر پیام خطا"""
    if token:
        message = message.replace(token, "***")
    return (message or "").strip()[:400] or "git error"


def build_site(cfg, progress_cb=None):
    """
    ساخت پروژه سایت پویا از خروجی کلون.
    cfg: {job_dir, project_dir, site_name, languages, admin_username, admin_password,
          theme_color, tagline, features{chat}, git_url, git_token}
    خروجی: dict نتیجه
    """
    cb = progress_cb or (lambda p, m: None)
    job_dir = cfg.get("job_dir") or ""
    project_dir = cfg.get("project_dir") or ""
    site_name = (cfg.get("site_name") or "").strip()
    password = cfg.get("admin_password") or ""
    langs = cfg.get("languages") or ["fa"]
    langs = [l for l in langs if l in ("fa", "en", "ar")] or ["fa"]

    if not site_name:
        raise BuildError("empty_site_name")
    if not project_dir:
        raise BuildError("empty_project_dir")
    if len(password) < 4:
        raise BuildError("weak_password")
    api_dir = os.path.join(job_dir, "api_data")
    media_dir = os.path.join(job_dir, "media")
    if not os.path.isdir(job_dir):
        raise BuildError("job_dir_missing")

    project_dir = os.path.abspath(project_dir)
    os.makedirs(project_dir, exist_ok=True)
    cfg["project_dir"] = project_dir
    cfg["languages"] = langs
    cfg["source_url"] = cfg.get("source_url", "")

    cb(5, "build:copy")
    # ۱) کپی قالب
    for root, dirs, files in os.walk(TEMPLATE_DIR):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        rel = os.path.relpath(root, TEMPLATE_DIR)
        dest_root = os.path.join(project_dir, rel) if rel != "." else project_dir
        os.makedirs(dest_root, exist_ok=True)
        for fname in files:
            shutil.copy2(os.path.join(root, fname), os.path.join(dest_root, fname))

    cb(15, "build:media")
    # ۲) رسانه‌ها + نگاشت
    media_map = _build_media_map(api_dir, media_dir)
    copied = _copy_media(media_dir, project_dir, cb)
    # نگاشت برای فایل‌هایی که دانلود نشده‌اند: نگاشت basename به خودش تا دست کم URL محلی درست باشد
    cfg["media_map"] = media_map

    cb(30, "build:db")
    # ۳) دیتابیس
    counts = _seed_database(project_dir, api_dir, cfg, media_map, cb)

    # ۴) config.json (بدون رمز متنی؛ فقط هش)
    salt_hash = hash_password_local(password)
    config = {
        "site_name": site_name,
        "tagline": cfg.get("tagline", ""),
        "languages": langs,
        "theme_color": cfg.get("theme_color") or "#4f46e5",
        "admin_username": (cfg.get("admin_username") or "admin").strip() or "admin",
        "admin_password_hash": salt_hash,
        "secret_key": secrets.token_hex(32),
        "features": {
            "chat": bool(cfg.get("features", {}).get("chat", True)),
            "multilingual": len(langs) > 1,
            "a11y": True,
        },
        "media_map": media_map,
    }
    with open(os.path.join(project_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=1)

    cb(70, "build:verify")
    # ۵) تست سریع راه‌اندازی (import سرور بدون اجرا)
    ok, detail = _verify_project(project_dir)
    result = {
        "ok": ok,
        "project_dir": project_dir,
        "counts": counts,
        "media_copied": copied,
        "git": None,
        "verify": detail,
    }
    if not ok:
        result["ok"] = False
        return result

    # ۶) گیت
    if cfg.get("git_url"):
        try:
            pushed, message = git_publish(project_dir, cfg.get("git_url"), cfg.get("git_token"), cb)
            result["git"] = {"pushed": pushed, "message": message}
        except (subprocess.TimeoutExpired, OSError) as e:
            result["git"] = {"pushed": False, "message": str(e)[:300]}

    cb(100, "build:done")
    result["ok"] = True
    return result


def _verify_project(project_dir):
    """بررسی سالم بودن پروژه ساخته‌شده — خروجی: (ok, detail)"""
    needed = ["app.py", "config.json", "database.db", "templates/base.html", "static/js/main.js"]
    missing = [n for n in needed if not os.path.exists(os.path.join(project_dir, n))]
    if missing:
        return False, "missing: " + ", ".join(missing)
    return True, "ok"


def hash_password_local(password):
    import hashlib
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return salt + "$" + digest
