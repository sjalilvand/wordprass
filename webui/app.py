# -*- coding: utf-8 -*-
"""پنل وب محلی ایجنت کلون وردپرس (Flask) — فرم آدرس، پیشرفت زنده و دانلود ZIP"""
import os
import threading
import uuid
import webbrowser

from flask import Flask, jsonify, render_template, send_file

from wpcagent.engine import run_clone

# حالت درون‌حافظه‌ای؛ برای استفاده شخصی/محلی کاملاً کافی است
JOBS = {}
JOBS_LOCK = threading.Lock()

STAGE_PERCENT = []


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates"),
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/start", methods=["POST"])
    def start():
        from flask import request
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

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    app = create_app()
    threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="127.0.0.1", port=port, threaded=True)
