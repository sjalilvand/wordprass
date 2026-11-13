# -*- coding: utf-8 -*-
"""
سایت‌ساز حرفه‌ای (نسخه ۲): از خروجی کلون وردپرس یک سایت پویا و کامل Next.js می‌سازد.
قالب هدف: سامانه‌ای شبیه نمونه «uastemdad» — پنل مدیریت کامل فارسی، چندزبانه (fa/en/ar)،
شخصی‌سازی نمایش، دسترسی‌پذیری توان‌خواهان، چت آنلاین هوشمند، PWA، تقویم شمسی و گالری.
Dynamic site builder v2: turns a WP clone output folder into a full professional Next.js site.
"""
import base64
import html
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from datetime import datetime
from urllib.parse import quote

from .utils import log

TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "site_template_next"
)

PALETTE = ["#0B5D51", "#C9A227", "#7C5CBF", "#0E7490", "#B4433A", "#15803D", "#B45309"]
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg", ".avif"}

# پیام‌های مرحله‌ای برای نوار پیشرفت پنل
STAGES = [
    ("copy", 6), ("media", 14), ("seed", 26), ("env", 32),
    ("docs", 38), ("install", 50), ("prisma", 64), ("seed_run", 74),
    ("verify", 86), ("git", 92), ("done", 100),
]


class BuildError(Exception):
    pass


def _cb(cb, key):
    """اعلام درصد بر اساس نقشه مراحل"""
    if not cb:
        return
    for k, pct in STAGES:
        if k == key:
            cb(pct, "build:" + key)
            return


# ----------------------------------------------------------------------------- helpers
def _load_json(api_dir, name):
    path = os.path.join(api_dir, name + ".json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (ValueError, OSError):
        return []


def _wp_text(value):
    """برداشت متن خالص از فیلد rendered وردپرس"""
    if isinstance(value, dict):
        value = value.get("rendered", "")
    text = re.sub(r"<[^>]+>", " ", value or "").replace("&nbsp;", " ").strip()
    return html.unescape(text)


def _wp_html(value):
    """HTML رندرشده وردپرس — کد کوتاه حذف، تگ‌ها حفظ می‌شود"""
    if isinstance(value, dict):
        value = value.get("rendered", "")
    text = re.sub(r"\[/?[^\]]{1,60}\]", "", value or "")
    # لینک‌های مطلق سایت مبدأ به مسیر نسبی
    src = ""
    return text


def _clean_date(value):
    if not value:
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return str(value).replace(" ", "T")[:19] + ".000Z"


def _slugify(title, fallback="post"):
    s = title.strip()[:60]
    return s if s else fallback


def _build_media_map(api_dir, media_dir):
    """نگاشت URL رسانه وردپرس به نام فایل محلی دانلودشده"""
    media_map = {}
    local_files = sorted(os.listdir(media_dir)) if os.path.isdir(media_dir) else []
    items = _load_json(api_dir, "media")
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


def _media_by_id(api_dir, media_map):
    by_id = {}
    for m in _load_json(api_dir, "media"):
        if isinstance(m, dict) and m.get("id"):
            local = media_map.get(m.get("source_url") or "")
            if local:
                by_id[m["id"]] = local
    return by_id


def _copy_media(media_dir, project_dir, cb=None):
    """کپی تصاویر دانلودشده به public/images/uploads"""
    uploads = os.path.join(project_dir, "public", "images", "uploads")
    os.makedirs(uploads, exist_ok=True)
    copied = 0
    if os.path.isdir(media_dir):
        for fname in os.listdir(media_dir):
            src = os.path.join(media_dir, fname)
            if not os.path.isfile(src):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext not in IMG_EXT:
                continue
            try:
                shutil.copy2(src, os.path.join(uploads, fname))
                copied += 1
                if cb and copied % 20 == 0:
                    cb(-1, "build:media")
            except OSError:
                pass
    return copied


def _short_name(name):
    words = (name or "").split()
    return " ".join(words[:4]) if len(words) > 4 else (name or "سامانه")


def _js_string(s):
    return json.dumps(s or "", ensure_ascii=False)


# ----------------------------------------------------------------------------- seed
def _generate_seed(api_dir, cfg, media_map, gallery_images, counts):
    """
    ساخت prisma/seed.ts از داده‌های واقعی سایت کلون‌شده.
    نگاشت محتوا:
      - نوشته‌های وردپرس  → اخبار (NEWS) و بخشی از تازه‌ترین‌ها → اطلاعیه (ANNOUNCEMENT)
      - برگه‌های وردپرس   → صفحات سایت (درباره ما و…)
      - دسته‌ها           → دسته‌بندی‌ها
      - تصاویر رسانه      → گالری + اسلایدر + تصویر شاخص اخبار
    """
    site_name = cfg.get("site_name") or "سامانه پویا"
    short = _short_name(site_name)
    tagline = cfg.get("tagline") or "سامانه رسمی — اخبار، اطلاعیه‌ها و خدمات"

    media_by_id = _media_by_id(api_dir, media_map)
    categories_json = _load_json(api_dir, "categories")
    tags_json = _load_json(api_dir, "tags")
    posts_json = _load_json(api_dir, "posts")
    pages_json = _load_json(api_dir, "pages")
    comments_json = _load_json(api_dir, "comments")

    used_slugs = set()
    used_names = set()

    def unique_slug(base, extra=""):
        cand = (base or extra or "item").strip()[:60] or "item"
        if cand in used_slugs:
            cand = f"{cand}-{secrets.token_hex(3)}"
        used_slugs.add(cand)
        return cand

    # ---------- دسته‌بندی‌ها
    cats = []
    for i, it in enumerate(categories_json[:14]):
        name = _wp_text(it.get("name")) or f"دسته {i + 1}"
        if name.lower() in used_names:
            continue
        used_names.add(name.lower())
        cats.append({
            "name": name,
            "slug": unique_slug(it.get("slug") or name),
            "color": PALETTE[i % len(PALETTE)],
        })

    wp_cat_slug = {}
    for src, dst in zip(categories_json[:14], cats):
        wp_cat_slug[src.get("id")] = dst["slug"]

    # ---------- نوشته‌ها
    ann_words = ("اطلاع", "اعلام", "announcement", "notice", "اخبار فوری")
    posts = []
    ann_posts = []
    for it in posts_json:
        if not isinstance(it, dict):
            continue
        title = _wp_text(it.get("title")) or "بدون عنوان"
        content = it.get("content")
        if isinstance(content, dict):
            content = content.get("rendered", "")
        content = re.sub(r"\[/?[^\]]{1,60}\]", "", content or "")
        excerpt_raw = it.get("excerpt")
        if isinstance(excerpt_raw, dict):
            excerpt_raw = excerpt_raw.get("rendered", "")
        excerpt = html.unescape(re.sub(r"<[^>]+>", " ", excerpt_raw or "")).strip()[:320]
        if not excerpt and content:
            excerpt = re.sub(r"<[^>]+>", " ", content)[:320]

        cover = ""
        fm = it.get("featured_media")
        if fm and fm in media_by_id:
            cover = "/images/uploads/" + quote(media_by_id[fm])

        wp_cat_ids = it.get("categories") or []
        cat_slug = None
        for cid in wp_cat_ids:
            if cid in wp_cat_slug:
                cat_slug = wp_cat_slug[cid]
                break
        cat_name = ""
        for cid in wp_cat_ids:
            for c in categories_json:
                if c.get("id") == cid:
                    cat_name = _wp_text(c.get("name"))
                    break
            if cat_name:
                break

        is_ann = bool(cat_name) and any(w in cat_name.lower() or w in cat_name for w in ann_words)

        p = {
            "title": title,
            "slug": unique_slug(it.get("slug") or title),
            "excerpt": excerpt,
            "content": content,
            "cover": cover,
            "cat": cat_slug,
            "type": "ANNOUNCEMENT" if is_ann else "NEWS",
            "featured": bool(fm) and it.get("status", "publish") == "publish",
            "at": _clean_date(it.get("date_gmt") or it.get("date")),
        }
        (ann_posts if is_ann else posts).append(p)

    # اگر اطلاعیه‌ای یافت نشد، سه نوشتهٔ تازه به‌عنوان اطلاعیه هم منتشر می‌شود
    if not ann_posts and posts:
        for src in posts[:3]:
            ann_posts.append({**src, "slug": unique_slug("ann-" + src["slug"])})

    # ---------- برگه‌ها → صفحات
    pages = []
    for i, it in enumerate(pages_json[:24]):
        if not isinstance(it, dict):
            continue
        title = _wp_text(it.get("title")) or f"صفحه {i + 1}"
        content = it.get("content")
        if isinstance(content, dict):
            content = content.get("rendered", "")
        content = re.sub(r"\[/?[^\]]{1,60}\]", "", content or "")
        excerpt = re.sub(r"<[^>]+>", " ", content or "")[:200]
        pages.append({
            "title": title,
            "slug": unique_slug(it.get("slug") or title),
            "excerpt": excerpt,
            "content": content,
            "icon": "file-text",
            "showInMenu": i < 7,
            "menuGroup": "about",
            "order": i,
        })
    # صفحه درباره ما اگر وجود نداشت
    if not any("درباره" in p["title"].lower() or "about" in p["slug"].lower() for p in pages):
        pages.append({
            "title": "درباره ما",
            "slug": unique_slug("about-us"),
            "excerpt": f"معرفی {site_name}",
            "content": f"<p>{site_name}</p><p>{tagline}</p>",
            "icon": "info",
            "showInMenu": True,
            "menuGroup": "about",
            "order": 0,
        })

    # ---------- اسلایدر (از اخبار تصویردار)
    slides = []
    featured = [p for p in posts if p["cover"]][:4]
    for i, p in enumerate(featured):
        slides.append({
            "title": p["title"][:90],
            "subtitle": p["excerpt"][:160],
            "imageUrl": p["cover"],
            "linkUrl": "/news/" + quote(p["slug"]),
            "order": i,
        })
    if len(slides) < 2 and gallery_images:
        for i, img in enumerate(gallery_images[: max(0, 4 - len(slides))]):
            slides.append({
                "title": site_name if i == 0 else tagline[:90],
                "subtitle": tagline[:160] if i == 0 else "",
                "imageUrl": img,
                "linkUrl": "/news",
                "order": len(slides) + i,
            })

    # ---------- سامانه‌های دسترسی سریع (از پیوندهای بیرونی منوی وردپرس)
    systems = []
    menu_items_json = _load_json(api_dir, "menu-items")
    src_host = ""
    try:
        from urllib.parse import urlparse
        src_host = urlparse(cfg.get("source_url") or "").netloc
    except Exception:
        src_host = ""
    for mi in menu_items_json:
        if len(systems) >= 4:
            break
        url = mi.get("url") or ""
        title = _wp_text(mi.get("title")) or ""
        if not url or not title:
            continue
        host = ""
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc
        except Exception:
            host = ""
        if host and src_host and host != src_host:
            systems.append({
                "title": title[:40],
                "url": url,
                "description": "",
                "icon": "monitor",
                "color": PALETTE[(len(systems) + 1) % len(PALETTE)],
                "order": len(systems),
            })

    # ---------- آمار و تنظیمات
    gallery_count = counts.get("gallery", 0)
    settings = {
        "siteName": site_name,
        "siteShort": short,
        "tagline": tagline,
        "logo": "",
        "address": "",
        "phones": "",
        "email": "",
        "presidentName": "",
        "presidentPhoto": "",
        "aboutText": (posts[0]["excerpt"][:200] if posts else f"سامانه رسمی {site_name}"),
        "statStudents": str(counts.get("posts", 0)),
        "stat1Label": "مطلب منتشرشده",
        "statFaculty": str(counts.get("pages", 0)),
        "stat2Label": "برگه سایت",
        "statPrograms": str(counts.get("categories", 0)),
        "stat3Label": "دسته‌بندی",
        "statBooks": str(gallery_count),
        "stat4Label": "تصویر در گالری",
        "mapUrl": "",
        "mapLat": "35.6892",
        "mapLng": "51.3890",
        "tickerEnabled": "1",
        "chatEnabled": "1" if cfg.get("features", {}).get("chat", True) else "0",
        "chatWelcome": (
            f"سلام! من دستیار هوشمند {short} هستم؛ درباره اخبار، اطلاعیه‌ها، "
            "صفحات سایت، آدرس و تلفن‌های تماس می‌توانید از من بپرسید."
        ),
        "footerNote": f"کلیه حقوق این سامانه متعلق به {site_name} می‌باشد.",
    }

    # ---------- منوی اصلی
    menu = [
        {"label": "خانه", "url": "/", "order": 0},
        {"label": "اخبار", "url": "/news", "order": 1},
        {"label": "اطلاعیه‌ها", "url": "/announcements", "order": 2},
    ]
    for s in systems:
        menu.append({"label": s["title"], "url": s["url"], "order": len(menu)})
    menu += [
        {"label": "درباره ما", "url": "/p/about-us", "order": len(menu)},
        {"label": "تماس با ما", "url": "/contact", "order": len(menu)},
    ]

    # ---------- عضو نمونه؟ خیر — فقط داده‌های واقعی سایت
    payload = {
        "admin": {
            "username": (cfg.get("admin_username") or "admin").strip() or "admin",
            "password": cfg.get("admin_password") or "admin123",
            "name": "مدیر سامانه",
        },
        "settings": settings,
        "categories": cats,
        "posts": posts[:60],
        "announcements": ann_posts[:20],
        "pages": pages,
        "slides": slides,
        "gallery": [
            {"title": os.path.splitext(os.path.basename(g))[0].replace("-", " ")[:60],
             "imageUrl": g, "order": i}
            for i, g in enumerate(gallery_images)
        ],
        "systems": systems,
        "menu": menu,
    }
    return payload


SEED_TEMPLATE = r'''/* eslint-disable */
// فایل تولیدشده توسط «ایجنت کلون وردپرس» — داده‌های واقعی سایت کلون‌شده
// Auto-generated seed from cloned WordPress data — do not edit by hand.
import { PrismaClient } from "@prisma/client";

const db = new PrismaClient();
const DATA = __WPC_DATA__;

async function main() {
  console.log("→ پاک‌سازی داده‌های قبلی");
  await db.chatMessage.deleteMany();
  await db.contactMessage.deleteMany();
  await db.galleryItem.deleteMany();
  await db.document.deleteMany();
  await db.program.deleteMany();
  await db.externalSystem.deleteMany();
  await db.relatedLink.deleteMany();
  await db.menuItem.deleteMany();
  await db.slide.deleteMany();
  await db.teamMember.deleteMany();
  await db.post.deleteMany();
  await db.page.deleteMany();
  await db.category.deleteMany();
  await db.setting.deleteMany();
  await db.user.deleteMany();
  await db.video.deleteMany();
  await db.faq.deleteMany();
  await db.event.deleteMany();
  await db.newsletterSubscriber.deleteMany();

  console.log("→ کاربر ادمین");
  const { hashPassword } = await import("../src/lib/auth");
  await db.user.create({
    data: {
      username: DATA.admin.username,
      passwordHash: hashPassword(DATA.admin.password),
      name: DATA.admin.name,
      role: "ADMIN",
    },
  });

  console.log("→ تنظیمات سایت");
  for (const [key, value] of Object.entries(DATA.settings)) {
    await db.setting.create({ data: { key, value } });
  }

  console.log("→ دسته‌بندی‌ها (" + DATA.categories.length + ")");
  const catBySlug = new Map<string, string>();
  for (const c of DATA.categories) {
    const row = await db.category.create({
      data: { name: c.name, slug: c.slug, color: c.color },
    });
    catBySlug.set(c.slug, row.id);
  }

  const createPost = async (p: { title: string; slug: string; excerpt: string; content: string; cover: string; cat: string | null; type: string; featured: boolean; at: string }) => {
    await db.post.create({
      data: {
        title: p.title,
        slug: p.slug,
        excerpt: p.excerpt,
        content: p.content,
        coverImage: p.cover || null,
        categoryId: p.cat ? (catBySlug.get(p.cat) ?? null) : null,
        type: p.type,
        featured: p.featured,
        published: true,
        publishedAt: new Date(p.at),
      },
    });
  };

  console.log("→ اخبار (" + DATA.posts.length + ")");
  for (const p of DATA.posts) await createPost(p);
  console.log("→ اطلاعیه‌ها (" + DATA.announcements.length + ")");
  for (const p of DATA.announcements) await createPost(p);

  console.log("→ صفحات (" + DATA.pages.length + ")");
  for (const p of DATA.pages) {
    await db.page.create({
      data: {
        title: p.title, slug: p.slug, excerpt: p.excerpt, content: p.content,
        icon: p.icon, showInMenu: p.showInMenu, menuGroup: p.menuGroup,
        order: p.order, published: true,
      },
    });
  }

  console.log("→ اسلایدر (" + DATA.slides.length + ")");
  for (const s of DATA.slides) {
    await db.slide.create({
      data: { title: s.title, subtitle: s.subtitle, imageUrl: s.imageUrl, linkUrl: s.linkUrl, order: s.order, isActive: true },
    });
  }

  console.log("→ گالری (" + DATA.gallery.length + ")");
  for (const g of DATA.gallery) {
    await db.galleryItem.create({
      data: { title: g.title, imageUrl: g.imageUrl, order: g.order, isActive: true },
    });
  }

  console.log("→ سامانه‌های دسترسی سریع (" + DATA.systems.length + ")");
  for (const s of DATA.systems) {
    await db.externalSystem.create({
      data: { title: s.title, url: s.url, description: s.description, icon: s.icon, color: s.color, order: s.order, isActive: true },
    });
  }

  console.log("→ منوی اصلی (" + DATA.menu.length + ")");
  for (const m of DATA.menu) {
    await db.menuItem.create({
      data: { label: m.label, url: m.url, location: "main", order: m.order, isActive: true },
    });
  }

  console.log("✅ Seed کامل شد — ورود به پنل: /admin با کاربری «" + DATA.admin.username + "»");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await db.$disconnect();
  });
'''


# ----------------------------------------------------------------------------- docs
def _write_env(project_dir):
    env = (
        "DATABASE_URL=file:../db/custom.db\n"
        f"AUTH_SECRET={secrets.token_hex(32)}\n"
        "NODE_OPTIONS=--max-old-space-size=4096\n"
    )
    with open(os.path.join(project_dir, ".env"), "w", encoding="utf-8", newline="\n") as f:
        f.write(env)


def _write_setup_ps1(project_dir, site_name, admin_user):
    ps = r'''# ============================================================
#  نصب و اجرای سایت ساخته‌شده (ویندوز / PowerShell)
#  اجرا:  PowerShell  →   .\setup.ps1
# ============================================================
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  نصب و راه‌اندازی سامانه" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""

# ---- ۱) بررسی Node.js (در صورت نبود، نصب خودکار با winget) ----
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "→ Node.js یافت نشد؛ تلاش برای نصب با winget ..." -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
        $node = Get-Command node -ErrorAction SilentlyContinue
    }
}
if (-not $node) {
    Write-Host "خطا: Node.js نصب نیست. ابتدا Node.js نسخه ۲۰ یا جدیدتر را از https://nodejs.org نصب کنید و دوباره اجرا کنید." -ForegroundColor Red
    exit 1
}
$nodeVersion = (node --version) -replace "v", ""
Write-Host "✓ Node.js نسخه $nodeVersion" -ForegroundColor Cyan

# ---- ۲) نصب وابستگی‌ها (فقط بار اول) ----
if (-not (Test-Path "node_modules")) {
    Write-Host "→ نصب وابستگی‌ها با npm (چند دقیقه طول می‌کشد) ..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) { Write-Host "خطا در نصب وابستگی‌ها" -ForegroundColor Red; exit 1 }
} else {
    Write-Host "✓ وابستگی‌ها از قبل نصب شده‌اند" -ForegroundColor Cyan
}

# ---- ۳) فایل .env ----
if (-not (Test-Path ".env")) {
    @"
DATABASE_URL=file:../db/custom.db
AUTH_SECRET=__SECRET__
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host "✓ فایل .env ساخته شد" -ForegroundColor Cyan
}

# ---- ۴) ساخت دیتابیس ----
New-Item -ItemType Directory -Force -Path "db" | Out-Null
Write-Host "→ ساخت و همگام‌سازی دیتابیس (prisma) ..." -ForegroundColor Yellow
npx prisma db push --accept-data-loss
if ($LASTEXITCODE -ne 0) { Write-Host "خطا در ساخت دیتابیس" -ForegroundColor Red; exit 1 }

# ---- ۵) داده‌های اولیه ----
if (-not (Test-Path "db\custom.db") -or ((Get-Item "db\custom.db").Length -lt 4096)) {
    Write-Host "→ بارگذاری داده‌های اولیه ..." -ForegroundColor Yellow
    npx tsx prisma/seed.ts
    if ($LASTEXITCODE -ne 0) { Write-Host "خطا در داده‌های اولیه" -ForegroundColor Red; exit 1 }
}

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  نصب کامل شد!" -ForegroundColor Green
Write-Host "  آدرس سایت:      http://localhost:3003" -ForegroundColor Yellow
Write-Host "  پنل مدیریت:     http://localhost:3003/admin" -ForegroundColor Yellow
Write-Host "  نام کاربری:     __ADMIN__" -ForegroundColor Yellow
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "→ اجرای سامانه روی پورت 3003 (برای توقف Ctrl+C) ..." -ForegroundColor Yellow
npm run dev:3003
'''
    ps = ps.replace("__SECRET__", secrets.token_hex(32)).replace("__ADMIN__", admin_user or "admin")
    with open(os.path.join(project_dir, "setup.ps1"), "w", encoding="utf-8-sig", newline="\r\n") as f:
        f.write(ps)


def _write_start_bat(project_dir):
    bat = (
        "@echo off\r\n"
        "rem اجرای خودکار سایت روی ویندوز — دوبار کلیک کنید\r\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -File \"%~dp0setup.ps1\"\r\n"
        "pause\r\n"
    )
    with open(os.path.join(project_dir, "START-SITE.bat"), "w", encoding="utf-8", newline="") as f:
        f.write(bat)


def _write_readme(project_dir, cfg, counts, git_ok):
    site_name = cfg.get("site_name") or "سامانه"
    langs = " / ".join(cfg.get("languages") or ["fa"])
    txt = f"""# {site_name}

سایت پویا و کامل ساخته‌شده توسط «ایجنت کلون وردپرس» از محتوای واقعی سایت کلون‌شده.
فناوری: Next.js 16 + TypeScript + Tailwind CSS 4 + shadcn/ui + Prisma + SQLite

## امکانات
- طراحی اختصاصی فارسی (RTL) با فونت وزیرمتن، تم روشن/تاریک، کاملاً واکنش‌گرا
- صفحه اصلی: اسلایدر، اخبار، اطلاعیه‌ها، نوار خبری متحرک، آمار متحرک، گالری، نقشه
- پنل مدیریت کامل فارسی: `/admin` — داشبورد، اخبار/اطلاعیه‌ها/صفحات/دسته‌ها، گالری،
  اسلایدر، منوها، پیام‌ها، مشترکان خبرنامه، آمار بازدید، تنظیمات و کاربران
- چندزبانه: {langs} (ترجمه خودکار رابط و تغییر جهت صفحه)
- شخصی‌سازی نمایش: فونت، اندازه متن، رنگ پس‌زمینه و ۷ تم رنگی
- دسترسی‌پذیری توان‌خواهان: کنتراست بالا، بزرگ‌نمایی متن، کاهش انیمیشن و…
- دستیار گفتگوی آنلاین (چت هوشمند) با موتور پاسخ محلی از روی داده‌های سایت
- فرم تماس (ذخیره در پنل)، خبرنامه، آمار بازدید، عضویت اعضا با تأیید مدیر
- PWA: نصب روی موبایل/دسکتاپ با کد QR و صفحه نصب `/app`
- تقویم شمسی، خواندن متن (TTS)، جستجو و صفحه‌بندی

## اجرا (ویندوز)
دوبار کلیک روی `START-SITE.bat` یا در PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\\setup.ps1          # نصب کامل + اجرا روی http://localhost:3003
```

## اجرا (لینوکس / مک)
```bash
npm install
npx prisma db push
npx tsx prisma/seed.ts
npm run dev:3003     # http://localhost:3003
```

## ورود به پنل مدیریت
- آدرس: `/admin`
- نام کاربری: `{cfg.get('admin_username') or 'admin'}`
- رمز عبور: همان رمزی که در پنل سایت‌ساز وارد کردید (پس از اولین ورود از بخش «کاربران» تغییر دهید)

## محتوای انتقال‌یافته
- اخبار: {counts.get('posts', 0)} | اطلاعیه‌ها: {counts.get('announcements', 0)} |
  صفحات: {counts.get('pages', 0)} | دسته‌بندی: {counts.get('categories', 0)} |
  اسلایدر: {counts.get('slides', 0)} | گالری: {counts.get('gallery', 0)}
- تصاویر در `public/images/uploads/`
- منبع کلون: {cfg.get('source_url') or '-'}

> توکن گیت در هیچ فایلی ذخیره نمی‌شود؛ {('مخزن به ' + (cfg.get('git_url') or '') + ' ارسال شد.') if git_ok else 'این پروژه به مخزن گیت ارسال نشده است.'}
"""
    with open(os.path.join(project_dir, "README.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write(txt)


# ----------------------------------------------------------------------------- npm/git
def _run(cmd, cwd, timeout=600, shell=False):
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, shell=shell,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except FileNotFoundError as e:
        return 127, str(e)


def _has_node():
    code, out = _run(["node", "--version"], os.getcwd(), timeout=15)
    return code == 0, out.strip()


def npm_install(project_dir, cb=None):
    cb and cb(44, "build:install")
    code, out = _run(["npm", "install", "--no-audit", "--no-fund", "--loglevel", "error"], project_dir, timeout=1500)
    if code != 0:
        return False, out[-1500:]
    return True, "ok"


def prisma_push(project_dir, cb=None):
    cb and cb(60, "build:prisma")
    code, out = _run(["npx", "prisma", "db", "push", "--accept-data-loss"], project_dir, timeout=420)
    if code != 0:
        return False, out[-1500:]
    return True, "ok"


def seed_run(project_dir, cb=None):
    cb and cb(72, "build:seed_run")
    code, out = _run(["npx", "tsx", "prisma/seed.ts"], project_dir, timeout=420)
    if code != 0:
        return False, out[-1500:]
    return True, "ok"


def git_publish(project_dir, repo_url, token, cb=None):
    """ساخت مخزن گیت و push — توکن فقط در حافظه پردازه استفاده می‌شود"""
    token = (token or "").strip()
    repo_url = (repo_url or "").strip()
    if not repo_url:
        return False, "no_repo"
    if "://" not in repo_url:
        is_fs_path = repo_url.startswith(("/", "./", "../", "~", os.sep)) or ":\\" in repo_url
        if not is_fs_path:
            repo_url = "https://" + repo_url
    clean_url = repo_url
    if token:
        push_url = repo_url.replace("https://", f"https://{token}@").replace("http://", f"http://{token}@")
    else:
        push_url = repo_url

    cb and cb(90, "build:git")
    code, out = _run(["git", "init"], project_dir)
    if code != 0 and "already exists" not in out:
        return False, _safe(out, token)
    _run(["git", "config", "user.name", "WordPress Clone Agent"], project_dir)
    _run(["git", "config", "user.email", "agent@local"], project_dir)
    # .gitignore مناسب پروژه Next.js
    gi = os.path.join(project_dir, ".gitignore")
    if not os.path.exists(gi):
        with open(gi, "w", encoding="utf-8", newline="\n") as f:
            f.write("node_modules/\n.next/\ndb/\n.env\n*.log\n")
    code, out = _run(["git", "add", "-A"], project_dir)
    if code != 0:
        return False, _safe(out, token)
    code, out = _run(["git", "commit", "-m", "Dynamic Next.js site built by WordPress Clone Agent"], project_dir)
    if code != 0 and "nothing to commit" not in out:
        return False, _safe(out, token)
    _run(["git", "branch", "-M", "main"], project_dir)
    _run(["git", "remote", "remove", "origin"], project_dir)
    code, out = _run(["git", "remote", "add", "origin", clean_url], project_dir)
    if code != 0:
        return False, _safe(out, token)
    cb and cb(94, "build:git_push")
    code, out = _run(["git", "push", push_url, "main"], project_dir, timeout=420)
    if code != 0:
        return False, _safe(out, token)
    return True, "pushed"


def _safe(message, token):
    if token:
        message = message.replace(token, "***")
    return (message or "").strip()[:400] or "git error"


# ----------------------------------------------------------------------------- main
def build_site(cfg, progress_cb=None):
    """
    ساخت پروژه Next.js حرفه‌ای از خروجی کلون.
    cfg: {job_dir, project_dir, site_name, tagline, languages, admin_username, admin_password,
          features{chat}, git_url, git_token, auto_install}
    """
    cb = progress_cb or (lambda p, m: None)
    job_dir = cfg.get("job_dir") or ""
    project_dir = cfg.get("project_dir") or ""
    site_name = (cfg.get("site_name") or "").strip()
    password = cfg.get("admin_password") or ""

    if not site_name:
        raise BuildError("empty_site_name")
    if not project_dir:
        raise BuildError("empty_project_dir")
    if len(password) < 4:
        raise BuildError("weak_password")
    if not os.path.isdir(TEMPLATE_DIR):
        raise BuildError("template_missing")
    api_dir = os.path.join(job_dir, "api_data")
    media_dir = os.path.join(job_dir, "media")
    if not os.path.isdir(job_dir):
        raise BuildError("job_dir_missing")

    project_dir = os.path.abspath(project_dir)
    os.makedirs(project_dir, exist_ok=True)
    cfg["project_dir"] = project_dir
    cfg["source_url"] = cfg.get("source_url", "")

    _cb(cb, "copy")
    # ۱) کپی قالب Next.js
    for root, dirs, files in os.walk(TEMPLATE_DIR):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "node_modules", ".next")]
        rel = os.path.relpath(root, TEMPLATE_DIR)
        dest_root = os.path.join(project_dir, rel) if rel != "." else project_dir
        os.makedirs(dest_root, exist_ok=True)
        for fname in files:
            shutil.copy2(os.path.join(root, fname), os.path.join(dest_root, fname))

    _cb(cb, "media")
    # ۲) رسانه‌ها + نگاشت
    media_map = _build_media_map(api_dir, media_dir)
    copied = _copy_media(media_dir, project_dir, cb)
    gallery_images = [
        "/images/uploads/" + quote(fname)
        for fname in sorted(os.listdir(os.path.join(project_dir, "public", "images", "uploads")))
    ][:18]

    _cb(cb, "seed")
    # ۳) ساخت seed از داده‌های واقعی
    counts_pre = {
        "posts": len([p for p in _load_json(api_dir, "posts") if isinstance(p, dict)]),
        "pages": len([p for p in _load_json(api_dir, "pages") if isinstance(p, dict)]),
        "categories": len(_load_json(api_dir, "categories")),
    }
    payload = _generate_seed(api_dir, cfg, media_map, gallery_images, counts_pre)
    counts = {
        "posts": len(payload["posts"]),
        "announcements": len(payload["announcements"]),
        "pages": len(payload["pages"]),
        "categories": len(payload["categories"]),
        "slides": len(payload["slides"]),
        "gallery": len(payload["gallery"]),
        "systems": len(payload["systems"]),
        "menu": len(payload["menu"]),
    }
    seed_ts = SEED_TEMPLATE.replace("__WPC_DATA__", json.dumps(payload, ensure_ascii=False))
    with open(os.path.join(project_dir, "prisma", "seed.ts"), "w", encoding="utf-8", newline="\n") as f:
        f.write(seed_ts)

    _cb(cb, "env")
    # ۴) .env + دیتابیس
    _write_env(project_dir)

    _cb(cb, "docs")
    # ۵) راهنما و اسکریپت‌های اجرا
    _write_setup_ps1(project_dir, site_name, cfg.get("admin_username") or "admin")
    _write_start_bat(project_dir)
    _write_readme(project_dir, cfg, counts_pre, bool(cfg.get("git_url")))
    with open(os.path.join(project_dir, "build-info.json"), "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
            "source": cfg.get("source_url", ""),
            "languages": cfg.get("languages") or ["fa"],
            "stack": "nextjs",
            "counts": counts,
            "media_files": copied,
        }, f, ensure_ascii=False, indent=1)

    # ۶) نصب خودکار (اختیاری؛ نیازمند Node.js)
    node_ok, node_ver = _has_node()
    steps = {"node": node_ver or "", "npm": None, "prisma": None, "seed": None}
    if cfg.get("auto_install", True) and node_ok:
        ok, out = npm_install(project_dir, cb)
        steps["npm"] = "ok" if ok else out[-300:]
        if ok:
            ok2, out2 = prisma_push(project_dir, cb)
            steps["prisma"] = "ok" if ok2 else out2[-300:]
            if ok2:
                ok3, out3 = seed_run(project_dir, cb)
                steps["seed"] = "ok" if ok3 else out3[-300:]
        if not ok:
            cb and cb(86, "build:install_manual_hint")
    elif not node_ok:
        cb and cb(86, "build:no_node")

    _cb(cb, "verify")
    # ۷) بررسی سلامت پروژه
    ok, detail = _verify_project(project_dir)

    result = {
        "ok": ok,
        "project_dir": project_dir,
        "stack": "nextjs",
        "counts": counts,
        "media_copied": copied,
        "steps": steps,
        "node": node_ver or "",
        "git": None,
        "verify": detail,
    }
    if not ok:
        result["ok"] = False
        return result

    # ۸) گیت
    if cfg.get("git_url"):
        try:
            pushed, message = git_publish(project_dir, cfg.get("git_url"), cfg.get("git_token"), cb)
            result["git"] = {"pushed": pushed, "message": message}
        except (subprocess.TimeoutExpired, OSError) as e:
            result["git"] = {"pushed": False, "message": str(e)[:300]}

    _cb(cb, "done")
    result["ok"] = True
    return result


def _verify_project(project_dir):
    needed = [
        "package.json", ".env", "prisma/seed.ts", "prisma/schema.prisma",
        "src/app/(site)/page.tsx", "src/app/admin/login/page.tsx",
        "public/images/uploads", "setup.ps1", "START-SITE.bat", "README.md",
    ]
    missing = [n for n in needed if not os.path.exists(os.path.join(project_dir, n))]
    if missing:
        return False, "missing: " + ", ".join(missing)
    db_path = os.path.join(project_dir, "db", "custom.db")
    db_ok = os.path.exists(db_path) and os.path.getsize(db_path) > 4096
    return True, "ok" + ("+db" if db_ok else "")
