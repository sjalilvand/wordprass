# -*- coding: utf-8 -*-
"""راه‌انداز پنل وب محلی"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def launch_webui(port=8765):
    from webui.app import create_app
    app = create_app()
    print(f"پنل وب ایجنت کلون وردپرس روی http://127.0.0.1:{port} اجرا شد")
    print("برای پایان دادن Ctrl+C را بزنید")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
