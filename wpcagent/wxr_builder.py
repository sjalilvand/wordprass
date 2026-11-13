# -*- coding: utf-8 -*-
"""
سازنده فایل خروجی WXR 1.2 (استاندارد Import وردپرس)
شامل: نوشته‌ها، برگه‌ها، رسانه‌ها، دسته‌ها، برچسب‌ها، دیدگاه‌ها،
نویسنده‌ها، منوها و انواع محتوای سفارشی.
"""
import datetime
import re
from email.utils import format_datetime
from urllib.parse import urlparse

from .utils import log

RSS_NS = (
    'xmlns:excerpt="http://wordpress.org/export/1.2/excerpt/" '
    'xmlns:content="http://purl.org/rss/1.0/modules/content/" '
    'xmlns:wfw="http://wellformedweb.org/CommentAPI/" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:wp="http://wordpress.org/export/1.2/"'
)


def cdata(text):
    """پوشش امن متن داخل CDATA"""
    if text is None:
        text = ""
    text = str(text)
    # ]] /> تقلبی را می‌شکند
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def wp_date(value):
    """تبدیل تاریخ ISO وردپرس به قالب WXR"""
    if not value:
        return ""
    s = str(value)
    try:
        s2 = s.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(s2)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return s.replace("T", " ")[:19]


def rfc822(value):
    if not value:
        return format_datetime(datetime.datetime.now().astimezone())
    try:
        dt = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return format_datetime(dt)
    except ValueError:
        return format_datetime(datetime.datetime.now().astimezone())


def strip_html(text, limit=120):
    txt = re.sub(r"<[^>]+>", " ", str(text or ""))
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:limit]


def uploads_suffix(source_url):
    """مسیر نسبی فایل نسبت به پوشه uploads (برای متای _wp_attached_file)"""
    path = urlparse(source_url or "").path
    if "/uploads/" in path:
        return path.split("/uploads/", 1)[1].lstrip("/")
    return path.lstrip("/")


class WxrBuilder:
    def __init__(self, site_info, data):
        self.site = site_info
        self.data = data or {}
        self.base_url = site_info.get("base_url", "")
        self.site_name = (site_info.get("site") or {}).get("name") or "WordPress Clone"
        self.site_desc = (site_info.get("site") or {}).get("description") or ""

    # ---------- نویسنده‌ها ----------
    def _users_map(self):
        m = {}
        for u in self.data.get("users") or []:
            m[u.get("id")] = {
                "login": u.get("slug") or ("user_" + str(u.get("id"))),
                "email": u.get("email") or "",
                "display": u.get("name") or u.get("slug") or "",
                "first": u.get("first_name") or "",
                "last": u.get("last_name") or "",
            }
        return m

    # ---------- تکسونومی‌ها ----------
    def _terms_blocks(self):
        out = []
        cats = self.data.get("categories") or []
        tags = self.data.get("tags") or []
        cat_map = {c.get("id"): c for c in cats}
        tag_map = {t.get("id"): t for t in tags}

        for c in cats:
            parent_id = c.get("parent") or 0
            parent_slug = ""
            if parent_id and parent_id in cat_map:
                parent_slug = cat_map[parent_id].get("slug") or ""
            out.append(
                "  <wp:category>\n"
                f"    <wp:term_id>{c.get('id', 0)}</wp:term_id>\n"
                f"    <wp:category_nicename>{cdata(c.get('slug', ''))}</wp:category_nicename>\n"
                f"    <wp:category_parent>{cdata(parent_slug)}</wp:category_parent>\n"
                f"    <wp:cat_name>{cdata(c.get('name', ''))}</wp:cat_name>\n"
                "  </wp:category>"
            )
        for t in tags:
            out.append(
                "  <wp:tag>\n"
                f"    <wp:term_id>{t.get('id', 0)}</wp:term_id>\n"
                f"    <wp:tag_slug>{cdata(t.get('slug', ''))}</wp:tag_slug>\n"
                f"    <wp:tag_name>{cdata(t.get('name', ''))}</wp:tag_name>\n"
                "  </wp:tag>"
            )
        # تکسونومی‌های سفارشی + nav_menu
        custom = self.data.get("custom_taxonomies") or {}
        for _name, meta in custom.items():
            for term in meta.get("terms") or []:
                out.append(
                    "  <wp:term>\n"
                    f"    <wp:term_id>{term.get('id', 0)}</wp:term_id>\n"
                    f"    <wp:term_taxonomy>{cdata(meta['slug'] if False else meta.get('slug', ''))}</wp:term_taxonomy>\n"
                    f"    <wp:term_slug>{cdata(term.get('slug', ''))}</wp:term_slug>\n"
                    f"    <wp:term_parent>{cdata('')}</wp:term_parent>\n"
                    f"    <wp:term_name>{cdata(term.get('name', ''))}</wp:term_name>\n"
                    "  </wp:term>"
                )
        for menu in self.data.get("menus") or []:
            out.append(
                "  <wp:term>\n"
                f"    <wp:term_id>{menu.get('id', 0)}</wp:term_id>\n"
                "    <wp:term_taxonomy>nav_menu</wp:term_taxonomy>\n"
                f"    <wp:term_slug>{cdata(menu.get('slug', ''))}</wp:term_slug>\n"
                f"    <wp:term_parent>{cdata('')}</wp:term_parent>\n"
                f"    <wp:term_name>{cdata(menu.get('name', ''))}</wp:term_name>\n"
                "  </wp:term>"
            )
        return out, cat_map, tag_map

    # ---------- آیتم‌های محتوا ----------
    def _content_item(self, post, post_type, users, cat_map, tag_map, comments_by_post):
        pid = post.get("id", 0)
        author_id = post.get("author")
        author = users.get(author_id) if author_id else None
        login = author["login"] if author else "admin"

        content = (post.get("content") or {}).get("rendered", "") if isinstance(post.get("content"), dict) else (post.get("content") or "")
        excerpt = (post.get("excerpt") or {}).get("rendered", "") if isinstance(post.get("excerpt"), dict) else (post.get("excerpt") or "")
        title = (post.get("title") or {}).get("rendered", "") if isinstance(post.get("title"), dict) else (post.get("title") or "")

        lines = [
            "<item>",
            f"  <title>{cdata(title)}</title>",
            f"  <link>{post.get('link', '')}</link>",
            f"  <pubDate>{rfc822(post.get('date_gmt') or post.get('date'))}</pubDate>",
            f"  <dc:creator>{cdata(login)}</dc:creator>",
            f"  <guid isPermaLink=\"false\">{post.get('guid', {}).get('rendered', post.get('link', ''))}</guid>",
            "  <description></description>",
            f"  <content:encoded>{cdata(content)}</content:encoded>",
            f"  <excerpt:encoded>{cdata(strip_html(excerpt) if excerpt else '')}</excerpt:encoded>",
            f"  <wp:post_id>{pid}</wp:post_id>",
            f"  <wp:post_date>{cdata(wp_date(post.get('date')))}</wp:post_date>",
            f"  <wp:post_date_gmt>{cdata(wp_date(post.get('date_gmt')))}</wp:post_date_gmt>",
            f"  <wp:comment_status>{cdata(post.get('comment_status', 'open'))}</wp:comment_status>",
            f"  <wp:ping_status>{cdata(post.get('ping_status', 'open'))}</wp:ping_status>",
            f"  <wp:post_name>{cdata(post.get('slug', ''))}</wp:post_name>",
            f"  <wp:status>{cdata(post.get('status', 'publish'))}</wp:status>",
            f"  <wp:post_parent>{post.get('parent', 0) or 0}</wp:post_parent>",
            f"  <wp:menu_order>{post.get('menu_order', 0) or 0}</wp:menu_order>",
            f"  <wp:post_type>{post_type}</wp:post_type>",
            f"  <wp:post_password>{cdata('')}</wp:post_password>",
            f"  <wp:is_sticky>{1 if post.get('sticky') else 0}</wp:is_sticky>",
        ]

        if post_type == "post":
            for cid in post.get("categories") or []:
                c = cat_map.get(cid)
                if c:
                    lines.append(
                        f"  <category domain=\"category\" nicename=\"{c.get('slug', '')}\">"
                        f"{cdata(c.get('name', ''))}</category>"
                    )
            for tid in post.get("tags") or []:
                t = tag_map.get(tid)
                if t:
                    lines.append(
                        f"  <category domain=\"post_tag\" nicename=\"{t.get('slug', '')}\">"
                        f"{cdata(t.get('name', ''))}</category>"
                    )

        if post.get("format") and post.get("format") != "standard":
            lines.append(f"  <category domain=\"post_format\" nicename=\"post-format-{post['format']}\">"
                         f"{cdata(post['format'])}</category>")

        # تصویر شاخص
        fm = post.get("featured_media") or 0
        if fm:
            lines.append(
                "  <wp:postmeta>\n"
                "    <wp:meta_key><![CDATA[_thumbnail_id]]></wp:meta_key>\n"
                f"    <wp:meta_value>{cdata(str(fm))}</wp:meta_value>\n"
                "  </wp:postmeta>"
            )

        # فیلدهای اضافی CPT
        if post_type not in ("post", "page"):
            tax_lines = []
            for tax_name, values in (post.get("taxonomies") or {}).items():
                pass  # REST استاندارد فیلد تکسونومی مستقیم نمی‌دهد؛ قابل گسترش
            del tax_lines

        for c in comments_by_post.get(pid, []):
            lines.extend(self._comment_block(c))

        lines.append("</item>")
        return "\n".join(lines)

    def _comment_block(self, c):
        approved = c.get("status", "approved")
        approved_val = "1" if approved == "approved" else "0"
        content = (c.get("content") or {}).get("rendered", "") if isinstance(c.get("content"), dict) else (c.get("content") or "")
        return [
            "  <wp:comment>",
            f"    <wp:comment_id>{c.get('id', 0)}</wp:comment_id>",
            f"    <wp:comment_author>{cdata(c.get('author_name', ''))}</wp:comment_author>",
            f"    <wp:comment_author_email>{cdata(c.get('author_email', ''))}</wp:comment_author_email>",
            f"    <wp:comment_author_url>{cdata(c.get('author_url', ''))}</wp:comment_author_url>",
            f"    <wp:comment_author_IP>{cdata('')}</wp:comment_author_IP>",
            f"    <wp:comment_date>{cdata(wp_date(c.get('date')))}</wp:comment_date>",
            f"    <wp:comment_date_gmt>{cdata(wp_date(c.get('date_gmt')))}</wp:comment_date_gmt>",
            f"    <wp:comment_content>{cdata(content)}</wp:comment_content>",
            f"    <wp:comment_approved>{cdata(approved_val)}</wp:comment_approved>",
            f"    <wp:comment_type>{cdata(c.get('type', '') or '')}</wp:comment_type>",
            f"    <wp:comment_parent>{c.get('parent', 0) or 0}</wp:comment_parent>",
            f"    <wp:comment_user_id>{c.get('user', 0) or 0}</wp:comment_user_id>",
            "  </wp:comment>",
        ]

    def _attachment_item(self, m, users):
        pid = m.get("id", 0)
        author_id = m.get("author")
        author = users.get(author_id) if author_id else None
        login = author["login"] if author else "admin"
        title = (m.get("title") or {}).get("rendered", "") if isinstance(m.get("title"), dict) else (m.get("title") or "")
        src = m.get("source_url") or ""
        post_parent = m.get("post") or 0
        lines = [
            "<item>",
            f"  <title>{cdata(title)}</title>",
            f"  <link>{m.get('link', '')}</link>",
            f"  <pubDate>{rfc822(m.get('date_gmt') or m.get('date'))}</pubDate>",
            f"  <dc:creator>{cdata(login)}</dc:creator>",
            f"  <guid isPermaLink=\"false\">{src}</guid>",
            "  <description></description>",
            f"  <content:encoded>{cdata(m.get('description', {}).get('rendered', '') if isinstance(m.get('description'), dict) else '')}</content:encoded>",
            f"  <excerpt:encoded>{cdata(m.get('caption', {}).get('rendered', '') if isinstance(m.get('caption'), dict) else '')}</excerpt:encoded>",
            f"  <wp:post_id>{pid}</wp:post_id>",
            f"  <wp:post_date>{cdata(wp_date(m.get('date')))}</wp:post_date>",
            f"  <wp:post_date_gmt>{cdata(wp_date(m.get('date_gmt')))}</wp:post_date_gmt>",
            f"  <wp:comment_status>{cdata(m.get('comment_status', 'open'))}</wp:comment_status>",
            f"  <wp:ping_status>{cdata(m.get('ping_status', 'closed'))}</wp:ping_status>",
            f"  <wp:post_name>{cdata(m.get('slug', ''))}</wp:post_name>",
            "  <wp:status><![CDATA[inherit]]></wp:status>",
            f"  <wp:post_parent>{post_parent}</wp:post_parent>",
            "  <wp:menu_order>0</wp:menu_order>",
            "  <wp:post_type>attachment</wp:post_type>",
            f"  <wp:post_password>{cdata('')}</wp:post_password>",
            "  <wp:is_sticky>0</wp:is_sticky>",
            f"  <wp:attachment_url>{cdata(src)}</wp:attachment_url>",
            "  <wp:postmeta>\n    <wp:meta_key><![CDATA[_wp_attached_file]]></wp:meta_key>\n"
            f"    <wp:meta_value>{cdata(uploads_suffix(src))}</wp:meta_value>\n  </wp:postmeta>",
        ]
        alt = m.get("alt_text") or ""
        if alt:
            lines.append(
                "  <wp:postmeta>\n    <wp:meta_key><![CDATA[_wp_attachment_image_alt]]></wp:meta_key>\n"
                f"    <wp:meta_value>{cdata(alt)}</wp:meta_value>\n  </wp:postmeta>"
            )
        lines.append("</item>")
        return "\n".join(lines)

    def _menu_item_block(self, item, menu_map):
        """تبدیل یک آیتم منو به post_type=nav_menu_item مطابق خروجی استاندارد وردپرس"""
        mid = item.get("id", 0)
        menu_id = None
        menus_field = item.get("menus") or []
        if menus_field:
            menu_id = menus_field[0]
        title = (item.get("title") or {}).get("rendered", "") if isinstance(item.get("title"), dict) else (item.get("title") or "")
        object_type = item.get("type", "custom")      # custom | post_type | taxonomy
        obj = item.get("object", "custom")
        object_id = item.get("object_id", 0) or 0
        url = item.get("url", "")
        target = item.get("target", "") or ""
        classes = item.get("classes") or []
        if isinstance(classes, list):
            classes_serialized = "a:" + str(len(classes)) + ":{" + "".join(
                f"i:{i};s:{len(c)}:\"{c}\";" for i, c in enumerate(classes)) + "}"
        else:
            classes_serialized = "a:0:{}"

        if object_type == "custom":
            mi_type = "custom"
            mi_object = "custom"
            mi_object_id = str(mid)
        elif object_type == "post_type":
            mi_type = "post_type"
            mi_object = obj
            mi_object_id = str(object_id)
        else:
            mi_type = "taxonomy"
            mi_object = obj
            mi_object_id = str(object_id)

        menu_slug = menu_map.get(menu_id, ("", ""))[0]
        menu_name = menu_map.get(menu_id, ("", ""))[1]

        lines = [
            "<item>",
            f"  <title>{cdata(title)}</title>",
            f"  <link>{url}</link>",
            f"  <pubDate>{rfc822(item.get('date_gmt') or item.get('date'))}</pubDate>",
            "  <dc:creator><![CDATA[admin]]></dc:creator>",
            f"  <guid isPermaLink=\"false\">{self.base_url}/?p={mid}</guid>",
            "  <description></description>",
            "  <content:encoded><![CDATA[]]></content:encoded>",
            "  <excerpt:encoded><![CDATA[]]></excerpt:encoded>",
            f"  <wp:post_id>{mid}</wp:post_id>",
            f"  <wp:post_date>{cdata(wp_date(item.get('date')))}</wp:post_date>",
            f"  <wp:post_date_gmt>{cdata(wp_date(item.get('date_gmt')))}</wp:post_date_gmt>",
            "  <wp:comment_status><![CDATA[closed]]></wp:comment_status>",
            "  <wp:ping_status><![CDATA[closed]]></wp:ping_status>",
            f"  <wp:post_name>{cdata(str(item.get('slug') or '') )}</wp:post_name>",
            "  <wp:status><![CDATA[publish]]></wp:status>",
            f"  <wp:post_parent>{item.get('menu_item_parent', 0) or 0}</wp:post_parent>",
            f"  <wp:menu_order>{item.get('menu_order', 0) or 0}</wp:menu_order>",
            "  <wp:post_type>nav_menu_item</wp:post_type>",
            f"  <wp:post_password>{cdata('')}</wp:post_password>",
            "  <wp:is_sticky>0</wp:is_sticky>",
            f"  <category domain=\"nav_menu\" nicename=\"{menu_slug}\">{cdata(menu_name)}</category>",
            "  <wp:postmeta>\n    <wp:meta_key><![CDATA[_menu_item_type]]></wp:meta_key>\n"
            f"    <wp:meta_value>{cdata(mi_type)}</wp:meta_value>\n  </wp:postmeta>",
            "  <wp:postmeta>\n    <wp:meta_key><![CDATA[_menu_item_menu_item_parent]]></wp:meta_key>\n"
            f"    <wp:meta_value>{cdata(str(item.get('menu_item_parent', 0) or 0))}</wp:meta_value>\n  </wp:postmeta>",
            "  <wp:postmeta>\n    <wp:meta_key><![CDATA[_menu_item_object_id]]></wp:meta_key>\n"
            f"    <wp:meta_value>{cdata(mi_object_id)}</wp:meta_value>\n  </wp:postmeta>",
            "  <wp:postmeta>\n    <wp:meta_key><![CDATA[_menu_item_object]]></wp:meta_key>\n"
            f"    <wp:meta_value>{cdata(mi_object)}</wp:meta_value>\n  </wp:postmeta>",
            "  <wp:postmeta>\n    <wp:meta_key><![CDATA[_menu_item_target]]></wp:meta_key>\n"
            f"    <wp:meta_value>{cdata(target)}</wp:meta_value>\n  </wp:postmeta>",
            "  <wp:postmeta>\n    <wp:meta_key><![CDATA[_menu_item_classes]]></wp:meta_key>\n"
            f"    <wp:meta_value>{cdata(classes_serialized)}</wp:meta_value>\n  </wp:postmeta>",
            "  <wp:postmeta>\n    <wp:meta_key><![CDATA[_menu_item_xfn]]></wp:meta_key>\n"
            "    <wp:meta_value><![CDATA[]]></wp:meta_value>\n  </wp:postmeta>",
            "  <wp:postmeta>\n    <wp:meta_key><![CDATA[_menu_item_url]]></wp:meta_key>\n"
            f"    <wp:meta_value>{cdata(url)}</wp:meta_value>\n  </wp:postmeta>",
            "</item>",
        ]
        return "\n".join(lines)

    # ---------- ساخت نهایی ----------
    def build(self):
        users = self._users_map()
        terms_blocks, cat_map, tag_map = self._terms_blocks()

        comments_by_post = {}
        for c in self.data.get("comments") or []:
            pid = c.get("post")
            if pid:
                comments_by_post.setdefault(pid, []).append(c)

        menu_map = {}
        for m in self.data.get("menus") or []:
            menu_map[m.get("id")] = (m.get("slug", ""), m.get("name", ""))

        items = []

        for p in self.data.get("posts") or []:
            items.append(self._content_item(p, "post", users, cat_map, tag_map, comments_by_post))
        for p in self.data.get("pages") or []:
            items.append(self._content_item(p, "page", users, cat_map, tag_map, comments_by_post))
        for _name, meta in (self.data.get("custom_types") or {}).items():
            for p in meta.get("items") or []:
                items.append(self._content_item(p, meta.get("slug", name), users, cat_map, tag_map, comments_by_post))
        for m in self.data.get("media") or []:
            items.append(self._attachment_item(m, users))
        for mi in self.data.get("menu_items") or []:
            items.append(self._menu_item_block(mi, menu_map))

        tz = (self.site.get("site") or {}).get("timezone_string") or ""

        parts = [
            '<?xml version="1.0" encoding="UTF-8" ?>',
            f'<rss version="2.0"\n  {RSS_NS}>',
            "<channel>",
            f"  <title>{cdata(self.site_name)}</title>",
            f"  <link>{self.base_url}</link>",
            f"  <description>{cdata(self.site_desc)}</description>",
            f"  <pubDate>{rfc822(None)}</pubDate>",
            f"  <language>{cdata('fa-IR' if not tz else tz)}</language>",
            "  <wp:wxr_version>1.2</wp:wxr_version>",
            f"  <wp:base_site_url>{self.base_url}</wp:base_site_url>",
            f"  <wp:base_blog_url>{self.base_url}</wp:base_blog_url>",
        ]

        for uid, u in users.items():
            parts.append(
                "  <wp:author>\n"
                f"    <wp:author_id>{uid}</wp:author_id>\n"
                f"    <wp:author_login>{cdata(u['login'])}</wp:author_login>\n"
                f"    <wp:author_email>{cdata(u['email'])}</wp:author_email>\n"
                f"    <wp:author_display_name>{cdata(u['display'])}</wp:author_display_name>\n"
                f"    <wp:author_first_name>{cdata(u['first'])}</wp:author_first_name>\n"
                f"    <wp:author_last_name>{cdata(u['last'])}</wp:author_last_name>\n"
                "  </wp:author>"
            )

        parts.extend(terms_blocks)
        parts.extend(items)

        parts.append("</channel>")
        parts.append("</rss>")

        return "\n".join(parts)


def build_wxr(site_info, data, out_path):
    """ساخت و ذخیره فایل WXR؛ خروجی: تعداد آیتم‌ها"""
    xml = WxrBuilder(site_info, data).build()
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(xml)
    n_items = xml.count("<item>")
    log.info("[OK] فایل WXR ساخته شد: %s (%s آیتم)", out_path, n_items)
    return n_items
