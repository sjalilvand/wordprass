#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
سایت پویا — ساخته‌شده توسط ایجنت کلون وردپرس (WordPress Clone Agent)
Dynamic site generated from a cloned WordPress site.

اجرا:
    python app.py            ->  http://127.0.0.1:8766
    پنل ادمین:  http://127.0.0.1:8766/admin
"""
import json
import os
import re
import secrets
import sqlite3
import hashlib
import html as html_lib
from datetime import datetime
from functools import wraps

from flask import (
    Flask, g, request, session, redirect, abort, jsonify,
    render_template, send_from_directory, flash, get_flashed_messages,
)

ROOT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- config
with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as _f:
    CONFIG = json.load(_f)

LANGS = CONFIG.get("languages") or ["fa"]
PRIMARY_LANG = LANGS[0]
DB_PATH = os.path.join(ROOT, "database.db")
UPLOAD_DIR = os.path.join(ROOT, "static", "uploads")


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return salt + "$" + digest


def verify_password(password, stored):
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(hash_password(password, salt).split("$")[1], digest)


# ---------------------------------------------------------------- i18n (رابط کاربری)
I18N = {
    "fa": {
        "dir": "rtl", "name": "فارسی",
        "home": "خانه", "blog": "نوشته‌ها", "pages": "برگه‌ها", "about": "درباره",
        "contact": "تماس", "search": "جستجو", "search_ph": "جستجو در سایت…",
        "latest": "آخرین نوشته‌ها", "categories": "دسته‌ها", "tags": "برچسب‌ها",
        "read_more": "ادامه مطلب", "related": "مطالب مرتبط", "comments": "دیدگاه‌ها",
        "add_comment": "دیدگاه شما", "your_name": "نام شما", "your_email": "ایمیل (اختیاری)",
        "send_comment": "ثبت دیدگاه", "no_comments": "هنوز دیدگاهی ثبت نشده است.",
        "no_posts": "موردی یافت نشد.", "prev": "قبلی", "next": "بعدی",
        "results_for": "نتایج جستجو برای", "category": "دسته", "tag": "برچسب",
        "contact_title": "تماس با ما", "contact_send": "ارسال پیام",
        "contact_ok": "پیام شما ثبت شد. سپاس!", "msg_name": "نام", "msg_email": "ایمیل",
        "msg_body": "پیام شما", "theme_dark": "حالت تیره", "theme_light": "حالت روشن",
        "a11y_title": "ابزارهای دسترس‌پذیری", "a11y_font": "اندازه متن",
        "a11y_contrast": "کنتراست بالا", "a11y_motion": "کاهش انیمیشن",
        "chat_title": "گفتگوی آنلاین", "chat_ph": "سؤال خود را بنویسید…",
        "chat_hello": "سلام! درباره این سایت هر سؤالی دارید بپرسید.",
        "chat_send": "ارسال", "chat_you": "شما", "chat_bot": "پشتیبان",
        "skip": "پرش به محتوا", "lang_label": "زبان", "home_tagline": "وب‌سایت رسمی",
        "posted_in": "در", "by": "نوشته‌شده در", "min_read": "دقیقه مطالعه",
        "all": "همه", "page": "صفحه", "bad_login": "نام کاربری یا رمز اشتباه است",
    },
    "en": {
        "dir": "ltr", "name": "English",
        "home": "Home", "blog": "Posts", "pages": "Pages", "about": "About",
        "contact": "Contact", "search": "Search", "search_ph": "Search the site…",
        "latest": "Latest posts", "categories": "Categories", "tags": "Tags",
        "read_more": "Read more", "related": "Related posts", "comments": "Comments",
        "add_comment": "Your comment", "your_name": "Your name", "your_email": "Email (optional)",
        "send_comment": "Post comment", "no_comments": "No comments yet.",
        "no_posts": "Nothing found.", "prev": "Previous", "next": "Next",
        "results_for": "Search results for", "category": "Category", "tag": "Tag",
        "contact_title": "Contact us", "contact_send": "Send message",
        "contact_ok": "Your message was received. Thanks!", "msg_name": "Name", "msg_email": "Email",
        "msg_body": "Your message", "theme_dark": "Dark mode", "theme_light": "Light mode",
        "a11y_title": "Accessibility tools", "a11y_font": "Text size",
        "a11y_contrast": "High contrast", "a11y_motion": "Reduce motion",
        "chat_title": "Live chat", "chat_ph": "Type your question…",
        "chat_hello": "Hi! Ask anything about this site.",
        "chat_send": "Send", "chat_you": "You", "chat_bot": "Support",
        "skip": "Skip to content", "lang_label": "Language", "home_tagline": "Official website",
        "posted_in": "in", "by": "Posted on", "min_read": "min read",
        "all": "All", "page": "Page", "bad_login": "Wrong username or password",
    },
    "ar": {
        "dir": "rtl", "name": "العربية",
        "home": "الرئيسية", "blog": "المقالات", "pages": "الصفحات", "about": "حول",
        "contact": "اتصل بنا", "search": "بحث", "search_ph": "ابحث في الموقع…",
        "latest": "أحدث المقالات", "categories": "التصنيفات", "tags": "الوسوم",
        "read_more": "اقرأ المزيد", "related": "مقالات ذات صلة", "comments": "التعليقات",
        "add_comment": "تعليقك", "your_name": "اسمك", "your_email": "البريد (اختياري)",
        "send_comment": "إرسال التعليق", "no_comments": "لا توجد تعليقات بعد.",
        "no_posts": "لا يوجد شيء.", "prev": "السابق", "next": "التالي",
        "results_for": "نتائج البحث عن", "category": "التصنيف", "tag": "الوسم",
        "contact_title": "اتصل بنا", "contact_send": "إرسال الرسالة",
        "contact_ok": "تم استلام رسالتك. شكراً!", "msg_name": "الاسم", "msg_email": "البريد",
        "msg_body": "رسالتك", "theme_dark": "الوضع الداكن", "theme_light": "الوضع الفاتح",
        "a11y_title": "أدوات إمكانية الوصول", "a11y_font": "حجم النص",
        "a11y_contrast": "تباين عالٍ", "a11y_motion": "تقليل الحركة",
        "chat_title": "دردشة مباشرة", "chat_ph": "اكتب سؤالك…",
        "chat_hello": "مرحباً! اسأل أي شيء عن هذا الموقع.",
        "chat_send": "إرسال", "chat_you": "أنت", "chat_bot": "الدعم",
        "skip": "الانتقال إلى المحتوى", "lang_label": "اللغة", "home_tagline": "الموقع الرسمي",
        "posted_in": "في", "by": "نُشر في", "min_read": "دقيقة قراءة",
        "all": "الكل", "page": "صفحة", "bad_login": "اسم المستخدم أو كلمة المرور غير صحيحة",
    },
}

STOPWORDS = {
    "fa": {"از", "به", "که", "این", "را", "با", "برای", "و", "در", "است", "هست", "چه", "چگونه",
           "چیست", "می", "بر", "تا", "هم", "یک", "شما", "ما", "آن", "ها", "کردن", "شود", "درباره"},
    "en": {"the", "a", "an", "of", "to", "in", "is", "are", "what", "how", "for", "and", "or",
           "on", "it", "this", "that", "with", "you", "we", "i", "do", "does", "about", "can"},
    "ar": {"من", "إلى", "عن", "في", "هذا", "هذه", "ما", "هو", "هي", "على", "مع", "و", "أو",
           "كيف", "ماذا", "هل", "التي", "الذي", "أن", "إن", "لا", "بين", "أي"},
}


def current_lang():
    if session.get("lang") in LANGS:
        return session["lang"]
    qlang = request.args.get("lang")
    if qlang in LANGS:
        return qlang
    return PRIMARY_LANG


def T(key):
    lang = current_lang()
    return I18N.get(lang, I18N[PRIMARY_LANG]).get(key) or I18N["en"].get(key) or key


# ---------------------------------------------------------------- database
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS content(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ctype TEXT NOT NULL,            -- post | page
  title TEXT NOT NULL, slug TEXT UNIQUE NOT NULL,
  content TEXT DEFAULT '', excerpt TEXT DEFAULT '',
  status TEXT DEFAULT 'publish', image TEXT DEFAULT '',
  created_at TEXT DEFAULT '', menu_order INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS terms(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ttype TEXT NOT NULL, name TEXT NOT NULL, slug TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS content_terms(content_id INTEGER, term_id INTEGER);
CREATE TABLE IF NOT EXISTS comments(
  id INTEGER PRIMARY KEY AUTOINCREMENT, content_id INTEGER,
  author TEXT DEFAULT '', email TEXT DEFAULT '', body TEXT DEFAULT '',
  created_at TEXT DEFAULT '', approved INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS translations(
  id INTEGER PRIMARY KEY AUTOINCREMENT, object_id INTEGER, lang TEXT, field TEXT, value TEXT
);
CREATE TABLE IF NOT EXISTS conversations(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT DEFAULT '', created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS chat_messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT, conv_id INTEGER,
  sender TEXT DEFAULT 'visitor', body TEXT DEFAULT '', created_at TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS contact_messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, email TEXT, body TEXT,
  created_at TEXT DEFAULT '', is_read INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS menu_items(
  id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, url TEXT, position INTEGER DEFAULT 0
);
"""


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def q(sql, args=(), one=False):
    cur = db().execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def exec_sql(sql, args=()):
    cur = db().execute(sql, args)
    db().commit()
    return cur.lastrowid


def get_setting(key, default=""):
    row = q("SELECT v FROM settings WHERE k=?", (key,), one=True)
    return row["v"] if row else default


def set_setting(key, value):
    exec_sql("INSERT INTO settings(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (key, value))


# ---------------------------------------------------------------- app
app = Flask(__name__)
app.secret_key = CONFIG.get("secret_key") or secrets.token_hex(32)


@app.teardown_appcontext
def close_db(exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


@app.context_processor
def inject_globals():
    def tr(text, field="title", obj=None):
        """ترجمه دستی ذخیره‌شده در ادمین؛ در نبود آن متن اصلی"""
        if obj is not None:
            row = q("SELECT value FROM translations WHERE object_id=? AND lang=? AND field=?",
                    (obj["id"], current_lang(), field), one=True)
            if row and row["value"].strip():
                return row["value"]
        return text

    menu = q("SELECT * FROM menu_items ORDER BY position, id")
    cats = q("SELECT t.*, (SELECT COUNT(*) FROM content_terms ct JOIN content c ON c.id=ct.content_id "
             "WHERE ct.term_id=t.id AND c.ctype='post') AS n FROM terms t WHERE ttype='category' ORDER BY name")
    return {
        "t": T, "L": I18N.get(current_lang(), I18N[PRIMARY_LANG]),
        "LANG": current_lang(), "LANGS": LANGS, "I18N": I18N,
        "site_name": get_setting("site_name", CONFIG.get("site_name", "My Site")),
        "site_tagline": get_setting("tagline", CONFIG.get("tagline", "")),
        "theme_color": get_setting("theme_color", CONFIG.get("theme_color", "#4f46e5")),
        "menu": menu, "cats": cats, "chat_enabled": CONFIG.get("features", {}).get("chat", True),
        "chat_greeting": get_setting("chat_greeting", I18N.get(current_lang(), I18N[PRIMARY_LANG])["chat_hello"]),
        "tr": tr, "strip_html": strip_html, "get_setting": get_setting,
        "q": q, "media_url": media_url,
    }


def media_url(value):
    """مسیر تصویر شاخص: اگر فایل محلی باشد از uploads وگرنه آدرس کامل"""
    value = value or ""
    if value.startswith("http"):
        return value
    if value.startswith("/static/uploads/") or value.startswith("/uploads/"):
        return value if value.startswith("/static/") else "/static" + value
    return "/static/uploads/" + value if value else ""


def strip_html(text, limit=180):
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html_lib.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def slugify(text):
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w\u0600-\u06FF]+", "-", text, flags=re.UNICODE)
    return text.strip("-")[:80] or "item"


def unique_slug(base, exclude_id=None):
    slug, n = slugify(base), 2
    while True:
        row = q("SELECT id FROM content WHERE slug=? AND id IS NOT ?", (slug, exclude_id), one=True) \
            if exclude_id else q("SELECT id FROM content WHERE slug=?", (slug,), one=True)
        if not row:
            return slug
        slug = f"{slugify(base)}-{n}"
        n += 1


def relink_images(html_text):
    """تصاویر وردپرسی را به مسیر محلی uploads نگاشت می‌کند (اگر فایل موجود باشد)"""
    url_map = CONFIG.get("media_map") or {}
    if not html_text:
        return html_text

    def repl(m):
        attr, quote, url = m.group(1), m.group(2), m.group(3)
        local = url_map.get(url) or url_map.get(url.rstrip("/"))
        if not local and "/wp-content/uploads/" in url:
            base = url.rsplit("/", 1)[-1].split("?")[0].split("#")[0]
            local = url_map.get("basename:" + base)
        if local:
            return attr + "=" + quote + "/static/uploads/" + local + quote
        return m.group(0)

    return re.sub(r"""(src|href)=(["'])(https?://[^"']+)(["'])""", repl, html_text)


# ---------------------------------------------------------------- public routes
@app.route("/")
def home():
    posts = q("SELECT * FROM content WHERE ctype='post' AND status='publish' ORDER BY created_at DESC LIMIT 6")
    pages = q("SELECT * FROM content WHERE ctype='page' AND status='publish' ORDER BY menu_order LIMIT 4")
    total = q("SELECT COUNT(*) AS n FROM content WHERE ctype='post' AND status='publish'", one=True)["n"]
    return render_template("index.html", posts=posts, pages=pages, total=total)


@app.route("/blog")
def blog():
    page_no = max(1, int(request.args.get("p", 1) or 1))
    per_page = 8
    offset = (page_no - 1) * per_page
    rows = q("SELECT * FROM content WHERE ctype='post' AND status='publish' "
             "ORDER BY created_at DESC LIMIT ? OFFSET ?", (per_page, offset))
    total = q("SELECT COUNT(*) AS n FROM content WHERE ctype='post' AND status='publish'", one=True)["n"]
    return render_template("list.html", items=rows, title=T("blog"), total=total,
                           page_no=page_no, per_page=per_page, base="/blog", heading=T("blog"))


@app.route("/post/<slug>")
def post_detail(slug):
    item = q("SELECT * FROM content WHERE slug=? AND ctype IN ('post','page') AND status='publish'", (slug,), one=True)
    if not item:
        abort(404)
    item = dict(item)
    item["content"] = relink_images(item["content"])
    comments = q("SELECT * FROM comments WHERE content_id=? AND approved=1 ORDER BY created_at", (item["id"],))
    related = q("SELECT DISTINCT c.* FROM content c JOIN content_terms ct ON ct.content_id=c.id "
                "WHERE ct.term_id IN (SELECT term_id FROM content_terms WHERE content_id=?) "
                "AND c.id != ? AND c.status='publish' LIMIT 3", (item["id"], item["id"]))
    return render_template("single.html", item=item, comments=comments, related=related)


@app.route("/page/<slug>")
def page_detail(slug):
    return post_detail(slug)


@app.route("/category/<slug>")
def category(slug):
    term = q("SELECT * FROM terms WHERE slug=? AND ttype='category'", (slug,), one=True)
    if not term:
        abort(404)
    rows = q("SELECT c.* FROM content c JOIN content_terms ct ON ct.content_id=c.id "
             "WHERE ct.term_id=? AND c.status='publish' ORDER BY c.created_at DESC", (term["id"],))
    return render_template("list.html", items=rows, title=term["name"], total=len(rows),
                           page_no=1, per_page=len(rows) or 1, base="", heading=T("category") + ": " + term["name"])


@app.route("/tag/<slug>")
def tag(slug):
    term = q("SELECT * FROM terms WHERE slug=? AND ttype='tag'", (slug,), one=True)
    if not term:
        abort(404)
    rows = q("SELECT c.* FROM content c JOIN content_terms ct ON ct.content_id=c.id "
             "WHERE ct.term_id=? AND c.status='publish' ORDER BY c.created_at DESC", (term["id"],))
    return render_template("list.html", items=rows, title=term["name"], total=len(rows),
                           page_no=1, per_page=len(rows) or 1, base="", heading=T("tag") + ": " + term["name"])


@app.route("/search")
def search():
    term = (request.args.get("q") or "").strip()
    rows = []
    if term:
        like = f"%{term}%"
        rows = q("SELECT * FROM content WHERE status='publish' AND (title LIKE ? OR excerpt LIKE ? "
                 "OR content LIKE ?) ORDER BY created_at DESC LIMIT 50", (like, like, like))
    return render_template("list.html", items=rows, title=T("search"), total=len(rows),
                           page_no=1, per_page=len(rows) or 1, base="",
                           heading=T("results_for") + f' «{term}»')


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()[:100]
        email = (request.form.get("email") or "").strip()[:150]
        body = (request.form.get("body") or "").strip()[:4000]
        if name and body:
            exec_sql("INSERT INTO contact_messages(name, email, body, created_at) VALUES(?,?,?,?)",
                     (name, email, body, datetime.utcnow().strftime("%Y-%m-%d %H:%M")))
            flash(T("contact_ok"))
            return redirect("/contact")
    return render_template("contact.html")


@app.route("/comment/<int:content_id>", methods=["POST"])
def add_comment(content_id):
    author = (request.form.get("author") or "").strip()[:100]
    body = (request.form.get("body") or "").strip()[:3000]
    if author and body:
        exec_sql("INSERT INTO comments(content_id, author, body, created_at, approved) VALUES(?,?,?,?,0)",
                 (content_id, author, body, datetime.utcnow().strftime("%Y-%m-%d %H:%M")))
    return redirect(request.form.get("back") or "/blog")


@app.route("/set-lang/<lang>")
def set_lang(lang):
    if lang in LANGS:
        session["lang"] = lang
    return redirect(request.args.get("back") or request.referrer or "/")


# ---------------------------------------------------------------- chat bot (آفلاین، درباره همین سایت)
def _tokens(text, lang):
    text = re.sub(r"[^\w\u0600-\u06FF]+", " ", (text or "").lower(), flags=re.UNICODE)
    stop = STOPWORDS.get(lang, STOPWORDS["en"]) | STOPWORDS["en"] | STOPWORDS["fa"] | STOPWORDS["ar"]
    return [w for w in text.split() if len(w) > 1 and w not in stop]


def bot_reply(question):
    lang = current_lang()
    tokens = _tokens(question, lang)
    if not tokens:
        return get_setting("chat_fallback", I18N[lang]["chat_hello"])

    # ۱) پاسخ‌های آماده ادمین
    faq = get_setting("faq_pairs", "")
    for pair in faq.split("\n"):
        if "||" in pair:
            keys, answer = pair.split("||", 1)
            if any(k.strip() and k.strip().lower() in question.lower() for k in keys.split("|")):
                return answer.strip()

    # ۲) جستجو در محتوای سایت
    score_sql = """
      SELECT id, title, slug, ctype, excerpt, content,
             ( (title LIKE '%'||?||'%') * 5
             + (content LIKE '%'||?||'%') * 2 ) AS s
      FROM content WHERE status='publish'"""
    best, best_score = None, 0
    for row in q(score_sql + " AND (title LIKE ? OR content LIKE ?)",
                 (tokens[0], tokens[0], f"%{tokens[0]}%", f"%{tokens[0]}%")):
        score = 0
        blob = (row["title"] + " " + row["content"]).lower()
        for tk in tokens:
            score += blob.count(tk) * (5 if tk in row["title"].lower() else 2)
        if score > best_score:
            best, best_score = row, score

    if best and best_score >= 4:
        link = ("/post/" if best["ctype"] == "post" else "/page/") + best["slug"]
        snippet = strip_html(best["excerpt"] or best["content"], 220)
        return {"text": snippet, "link": link, "link_title": best["title"]}

    # ۳) پاسخ پیش‌فرض + پیشنهاد
    fallback = get_setting("chat_fallback", "")
    suggestions = q("SELECT title, slug, ctype FROM content WHERE status='publish' ORDER BY id LIMIT 4")
    sugg = [{"title": s["title"], "link": ("/post/" if s["ctype"] == "post" else "/page/") + s["slug"]}
            for s in suggestions]
    return {"text": fallback or I18N[lang]["chat_hello"], "suggestions": sugg}


@app.route("/chat/send", methods=["POST"])
def chat_send():
    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()[:2000]
    conv_id = data.get("conv_id")
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    if not conv_id:
        conv_id = exec_sql("INSERT INTO conversations(name, created_at) VALUES(?,?)",
                           (data.get("name") or "مهمان", now))
    if body:
        exec_sql("INSERT INTO chat_messages(conv_id, sender, body, created_at) VALUES(?,?,?,?)",
                 (conv_id, "visitor", body, now))
        reply = bot_reply(body)
        reply_text = reply["text"] if isinstance(reply, dict) else str(reply)
        exec_sql("INSERT INTO chat_messages(conv_id, sender, body, created_at) VALUES(?,?,?,?)",
                 (conv_id, "bot", reply_text, now))
    messages = q("SELECT sender, body, created_at FROM chat_messages WHERE conv_id=? ORDER BY id", (conv_id,))
    return jsonify({"conv_id": conv_id,
                    "messages": [dict(m) for m in messages],
                    "last_reply": reply if body else None})


@app.route("/chat/poll/<int:conv_id>")
def chat_poll(conv_id):
    messages = q("SELECT sender, body, created_at FROM chat_messages WHERE conv_id=? ORDER BY id", (conv_id,))
    return jsonify({"conv_id": conv_id, "messages": [dict(m) for m in messages]})


# ---------------------------------------------------------------- admin panel
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect("/admin/login")
        return fn(*args, **kwargs)
    return wrapper


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = ""
    if request.method == "POST":
        user = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        stored = CONFIG.get("admin_password_hash", "")
        if user == CONFIG.get("admin_username", "admin") and verify_password(password, stored):
            session["admin"] = user
            return redirect("/admin")
        error = T("bad_login")
    return render_template("admin/login.html", error=error)


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect("/admin/login")


@app.route("/admin")
@login_required
def admin_dashboard():
    stats = {
        "posts": q("SELECT COUNT(*) n FROM content WHERE ctype='post'", one=True)["n"],
        "pages": q("SELECT COUNT(*) n FROM content WHERE ctype='page'", one=True)["n"],
        "comments": q("SELECT COUNT(*) n FROM comments WHERE approved=0", one=True)["n"],
        "chats": q("SELECT COUNT(*) n FROM conversations", one=True)["n"],
        "messages": q("SELECT COUNT(*) n FROM contact_messages WHERE is_read=0", one=True)["n"],
    }
    recent = q("SELECT * FROM content ORDER BY id DESC LIMIT 6")
    return render_template("admin/dashboard.html", stats=stats, recent=recent)


@app.route("/admin/content")
@login_required
def admin_content():
    ctype = request.args.get("type", "post")
    rows = q("SELECT * FROM content WHERE ctype=? ORDER BY id DESC", (ctype,))
    return render_template("admin/content_list.html", items=rows, ctype=ctype)


@app.route("/admin/content/new", methods=["GET", "POST"])
@login_required
def admin_content_new():
    ctype = request.args.get("type", "post")
    if request.method == "POST":
        title = (request.form.get("title") or "بدون عنوان").strip()
        cid = exec_sql(
            "INSERT INTO content(ctype, title, slug, content, excerpt, status, created_at) VALUES(?,?,?,?,?,?,?)",
            (request.form.get("ctype", ctype), title, unique_slug(title),
             request.form.get("content", ""), request.form.get("excerpt", ""),
             request.form.get("status", "publish"), datetime.utcnow().strftime("%Y-%m-%d %H:%M")))
        return redirect(f"/admin/content/{cid}/edit")
    return render_template("admin/content_edit.html", item=None, ctype=ctype, translations=[])


@app.route("/admin/content/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def admin_content_edit(item_id):
    item = q("SELECT * FROM content WHERE id=?", (item_id,), one=True)
    if not item:
        abort(404)
    if request.method == "POST":
        title = (request.form.get("title") or item["title"]).strip()
        exec_sql("UPDATE content SET title=?, slug=?, content=?, excerpt=?, status=?, image=? WHERE id=?",
                 (title, unique_slug(request.form.get("slug") or title, exclude_id=item_id),
                  request.form.get("content", ""), request.form.get("excerpt", ""),
                  request.form.get("status", "publish"), request.form.get("image", ""), item_id))
        return redirect("/admin/content?type=" + item["ctype"])
    trans = q("SELECT * FROM translations WHERE object_id=?", (item_id,))
    return render_template("admin/content_edit.html", item=item, ctype=item["ctype"], translations=trans)


@app.route("/admin/content/<int:item_id>/delete", methods=["POST"])
@login_required
def admin_content_delete(item_id):
    exec_sql("DELETE FROM content WHERE id=?", (item_id,))
    exec_sql("DELETE FROM content_terms WHERE content_id=?", (item_id,))
    return redirect(request.referrer or "/admin/content")


@app.route("/admin/content/<int:item_id>/translate", methods=["POST"])
@login_required
def admin_translate(item_id):
    lang = request.form.get("lang")
    field = request.form.get("field")
    value = request.form.get("value", "")
    if lang in I18N and field in ("title", "excerpt", "content"):
        row = q("SELECT id FROM translations WHERE object_id=? AND lang=? AND field=?",
                (item_id, lang, field), one=True)
        if row:
            exec_sql("UPDATE translations SET value=? WHERE id=?", (value, row["id"]))
        else:
            exec_sql("INSERT INTO translations(object_id, lang, field, value) VALUES(?,?,?,?)",
                     (item_id, lang, field, value))
    return redirect(f"/admin/content/{item_id}/edit")


@app.route("/admin/comments", methods=["GET", "POST"])
@login_required
def admin_comments():
    if request.method == "POST":
        cid = request.form.get("id")
        action = request.form.get("action")
        if action == "approve":
            exec_sql("UPDATE comments SET approved=1 WHERE id=?", (cid,))
        elif action == "delete":
            exec_sql("DELETE FROM comments WHERE id=?", (cid,))
        return redirect("/admin/comments")
    rows = q("SELECT cm.*, c.title AS post_title FROM comments cm LEFT JOIN content c ON c.id=cm.content_id "
             "ORDER BY cm.approved, cm.id DESC")
    return render_template("admin/comments.html", items=rows)


@app.route("/admin/chat", methods=["GET", "POST"])
@login_required
def admin_chat():
    if request.method == "POST":
        conv = request.form.get("conv_id")
        reply = (request.form.get("reply") or "").strip()[:2000]
        if conv and reply:
            exec_sql("INSERT INTO chat_messages(conv_id, sender, body, created_at) VALUES(?,?,?,?)",
                     (conv, "admin", reply, datetime.utcnow().strftime("%Y-%m-%d %H:%M")))
        return redirect("/admin/chat")
    convs = q("SELECT c.*, (SELECT COUNT(*) FROM chat_messages m WHERE m.conv_id=c.id) AS n, "
              "(SELECT body FROM chat_messages m WHERE m.conv_id=c.id ORDER BY id DESC LIMIT 1) AS last_msg "
              "FROM conversations c ORDER BY c.id DESC")
    conv_id = request.args.get("conv", type=int)
    messages = q("SELECT * FROM chat_messages WHERE conv_id=? ORDER BY id", (conv_id,)) if conv_id else []
    return render_template("admin/chat.html", convs=convs, conv_id=conv_id, messages=messages)


@app.route("/admin/messages", methods=["GET", "POST"])
@login_required
def admin_messages():
    if request.method == "POST":
        exec_sql("DELETE FROM contact_messages WHERE id=?", (request.form.get("id"),))
        return redirect("/admin/messages")
    rows = q("SELECT * FROM contact_messages ORDER BY id DESC")
    return render_template("admin/messages.html", items=rows)


@app.route("/admin/media")
@login_required
def admin_media():
    items = []
    if os.path.isdir(UPLOAD_DIR):
        for fname in sorted(os.listdir(UPLOAD_DIR)):
            path = os.path.join(UPLOAD_DIR, fname)
            if os.path.isfile(path):
                items.append({"name": fname, "size": os.path.getsize(path), "url": "/static/uploads/" + fname})
    return render_template("admin/media.html", items=items)


@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    if request.method == "POST":
        for key in ("site_name", "tagline", "theme_color", "chat_greeting", "chat_fallback", "faq_pairs"):
            if key in request.form:
                set_setting(key, request.form.get(key, "").strip())
        flash("Saved")
        return redirect("/admin/settings")
    return render_template("admin/settings.html", langs=I18N)


# ---------------------------------------------------------------- errors & static
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8766"))
    print(f"[OK] {CONFIG.get('site_name', 'My Site')}  ->  http://127.0.0.1:{port}")
    print(f"[OK] Admin panel: http://127.0.0.1:{port}/admin  (user: {CONFIG.get('admin_username', 'admin')})")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
