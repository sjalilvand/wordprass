# -*- coding: utf-8 -*-
"""پنل وب محلی ایجنت کلون وردپرس (Flask) — کلون، سایت‌ساز پویا، پیش‌نمایش زنده"""
import atexit
import os
import socket
import subprocess
import sys
import threading
import uuid
import webbrowser

from flask import Flask, jsonify, render_template, request, send_file, send_from_directory

from wpcagent.engine import run_clone
from wpcagent.next_builder import build_site

# حالت درون‌حافظه‌ای؛ برای استفاده شخصی/محلی کاملاً کافی است
JOBS = {}
JOBS_LOCK = threading.Lock()

PREVIEWS = {}          # job_id -> {"proc": Popen, "port": int, "project_dir": str}
PREVIEW_LOCK = threading.Lock()


def _kill_all_previews():
    for info in PREVIEWS.values():
        try:
            info["proc"].terminate()
        except Exception:  # noqa: BLE001
            pass


atexit.register(_kill_all_previews)


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    # ------------------------------------------------------------ step 1-2: clone
    @app.route("/start", methods=["POST"])
    def start():
        url = (request.form.get("url") or "").strip()
        if not url:
            return jsonify({"error": "empty_url"}), 400
        if "://" not in url:
            url = "https://" + url

        limit_raw = (request.form.get("limit") or "").strip()
        limit = int(limit_raw) if limit_raw.isdigit() and int(limit_raw) > 0 else None
        max_pages = int(request.form.get("max_pages") or 100)
        do_mirror = request.form.get("mirror") == "on"
        do_api = request.form.get("api") == "on"
        do_wxr = request.form.get("wxr") == "on"
        do_zip = request.form.get("zip") == "on"
        if not (do_mirror or do_api or do_wxr):
            do_mirror = True

        job_id = uuid.uuid4().hex[:12]
        job = {
            "id": job_id,
            "url": url,
            "status": "running",
            "log": [],
            "percent": 0,
            "summary": None,
        }
        with JOBS_LOCK:
            JOBS[job_id] = job

        def cb(percent, message):
            with JOBS_LOCK:
                j = JOBS.get(job_id)
                if j is not None:
                    j["percent"] = percent
                    j["log"].append(message)
                    if len(j["log"]) > 400:
                        del j["log"][:100]

        def worker():
            try:
                summary = run_clone(
                    url,
                    out_root=os.path.join(os.getcwd(), "output"),
                    do_api=do_api, do_mirror=do_mirror, do_wxr=do_wxr, do_zip=do_zip,
                    limit=limit, max_pages=max_pages,
                    progress_cb=cb,
                )
                with JOBS_LOCK:
                    JOBS[job_id]["summary"] = summary
                    JOBS[job_id]["status"] = "done"
            except Exception as e:  # noqa: BLE001
                with JOBS_LOCK:
                    JOBS[job_id]["status"] = "error"
                    JOBS[job_id]["log"].append("خطا: " + str(e))

        threading.Thread(target=worker, daemon=True).start()
        return jsonify({"job_id": job_id})

    @app.route("/status/<job_id>")
    def status(job_id):
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if not job:
                return jsonify({"error": "not_found"}), 404
            payload = {
                "status": job["status"],
                "percent": job["percent"],
                "log": job["log"][-14:],
                "done": job["status"] != "running",
            }
            if job["status"] == "done" and job.get("summary"):
                s = job["summary"]
                paths = s.get("paths") or {}
                payload["summary"] = {
                    "counts": s.get("counts") or {},
                    "mirror": s.get("mirror") or {},
                    "wxr_items": s.get("wxr_items", 0),
                    "root": paths.get("root"),
                    "zip_ready": bool(paths.get("zip")),
                    "site_name": (s.get("site") or {}).get("name", ""),
                }
            return jsonify(payload)

    @app.route("/download/<job_id>")
    def download(job_id):
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if not job or job["status"] != "done":
                return "فایل آماده نیست", 404
            zip_path = (job.get("summary") or {}).get("paths", {}).get("zip")
        if zip_path and os.path.exists(zip_path):
            return send_file(zip_path, as_attachment=True)
        return "فایل ZIP ساخته نشده است", 404

    # ------------------------------------------------- پیش‌نمایش آینه استاتیک (بدون http.server دستی)
    @app.route("/preview-mirror/<job_id>/")
    @app.route("/preview-mirror/<job_id>/<path:filename>")
    def preview_mirror(job_id, filename="index.html"):
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if not job or job["status"] != "done":
                return "آینه آماده نیست", 404
            root = (job.get("summary") or {}).get("paths", {}).get("root")
        mirror_dir = os.path.join(root or "", "mirror")
        if not os.path.isdir(mirror_dir):
            return "پوشه mirror یافت نشد", 404
        target = os.path.normpath(os.path.join(mirror_dir, filename))
        if not target.startswith(os.path.abspath(mirror_dir)):
            return "مسیر نامعتبر", 400
        if os.path.isdir(target):
            target = os.path.join(target, "index.html")
        if not os.path.exists(target):
            return "یافت نشد", 404
        return send_file(target)

    # ------------------------------------------------------------ step 4: build dynamic site
    @app.route("/build/<job_id>", methods=["POST"])
    def build(job_id):
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if not job or job["status"] != "done":
                return jsonify({"error": "not_found"}), 404
            source_url = job["url"]
            job_root = (job.get("summary") or {}).get("paths", {}).get("root")

        cfg = {
            "job_dir": job_root,
            "source_url": source_url,
            "site_name": (request.form.get("site_name") or "").strip(),
            "project_dir": (request.form.get("project_dir") or "").strip(),
            "languages": request.form.getlist("langs"),
            "admin_username": (request.form.get("admin_user") or "admin").strip(),
            "admin_password": request.form.get("admin_pass") or "",
            "theme_color": (request.form.get("theme_color") or "#4f46e5").strip(),
            "tagline": (request.form.get("tagline") or "").strip(),
            "git_url": (request.form.get("git_url") or "").strip(),
            "git_token": (request.form.get("git_token") or "").strip(),
            "features": {"chat": request.form.get("chat") == "on"},
            "auto_install": request.form.get("auto_install") == "on",
        }
        if not cfg["site_name"] or not cfg["project_dir"] or len(cfg["admin_password"]) < 4:
            return jsonify({"error": "invalid_form"}), 400

        build_id = uuid.uuid4().hex[:12]
        build_job = {
            "id": build_id,
            "status": "running",
            "log": [],
            "percent": 0,
            "result": None,
            "clone_job": job_id,
            "cfg": {k: v for k, v in cfg.items() if k != "git_token"},
        }
        with JOBS_LOCK:
            JOBS[build_id] = build_job

        def bcb(percent, message):
            with JOBS_LOCK:
                b = JOBS.get(build_id)
                if b is not None:
                    b["percent"] = max(0, min(100, percent))
                    b["log"].append(message)
                    if len(b["log"]) > 300:
                        del b["log"][:80]

        def worker():
            try:
                result = build_site(cfg, bcb)
                with JOBS_LOCK:
                    JOBS[build_id]["result"] = result
                    JOBS[build_id]["status"] = "done"
            except Exception as e:  # noqa: BLE001
                with JOBS_LOCK:
                    JOBS[build_id]["status"] = "error"
                    JOBS[build_id]["log"].append("build_error:" + str(e))

        threading.Thread(target=worker, daemon=True).start()
        return jsonify({"build_id": build_id})

    @app.route("/status-build/<build_id>")
    def status_build(build_id):
        with JOBS_LOCK:
            b = JOBS.get(build_id)
            if not b:
                return jsonify({"error": "not_found"}), 404
            payload = {
                "status": b["status"],
                "percent": b["percent"],
                "log": b["log"][-12:],
                "done": b["status"] != "running",
            }
            if b["status"] == "done" and b.get("result"):
                r = b["result"]
                payload["result"] = {
                    "ok": r.get("ok"),
                    "project_dir": r.get("project_dir"),
                    "counts": r.get("counts") or {},
                    "media_copied": r.get("media_copied"),
                    "verify": r.get("verify"),
                    "git": r.get("git"),
                    "preview": PREVIEWS.get(build_id, {}).get("port"),
                }
            return jsonify(payload)

    # --------------------------------------------------------- preview: اجرای سایت ساخته‌شده به‌صورت زنده
    def _free_port(start=8766):
        port = start
        used = {info["port"] for info in PREVIEWS.values()}
        while port < start + 50:
            if port not in used:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    try:
                        s.bind(("127.0.0.1", port))
                        return port
                    except OSError:
                        port += 1
            else:
                port += 1
        return start

    @app.route("/preview/<build_id>", methods=["POST"])
    def preview(build_id):
        with JOBS_LOCK:
            b = JOBS.get(build_id)
            if not b or b["status"] != "done" or not (b.get("result") or {}).get("ok"):
                return jsonify({"error": "not_ready"}), 404
            project_dir = b["result"].get("project_dir")

        with PREVIEW_LOCK:
            old = PREVIEWS.get(build_id)
            if old:
                try:
                    old["proc"].terminate()
                except Exception:  # noqa: BLE001
                    pass
            port = _free_port()
            # سایت Next.js با npm run dev اجرا می‌شود (shell=True برای ویندوز/لینوکس)
            proc = subprocess.Popen(
                "npm run dev -- -p " + str(port),
                cwd=project_dir, shell=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            PREVIEWS[build_id] = {"proc": proc, "port": port, "project_dir": project_dir}
        return jsonify({"ok": True, "port": port, "url": f"http://127.0.0.1:{port}"})

    @app.route("/preview-stop/<build_id>", methods=["POST"])
    def preview_stop(build_id):
        with PREVIEW_LOCK:
            info = PREVIEWS.pop(build_id, None)
        if info:
            try:
                info["proc"].terminate()
            except Exception:  # noqa: BLE001
                pass
            return jsonify({"ok": True})
        return jsonify({"error": "not_running"}), 404

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    app = create_app()
    threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="127.0.0.1", port=port, threaded=True)
