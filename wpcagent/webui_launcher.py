# -*- coding: utf-8 -*-
"""راه‌انداز پنل وب محلی — باز شدن خودکار مرورگر"""
import os
import sys
import threading
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def launch_webui(port=8765, open_browser=True):
    from webui.app import create_app
    app = create_app()
    url = f"http://127.0.0.1:{port}"
    print(f"پنل وب ایجنت کلون وردپرس روی {url} اجرا شد")
    print("برای پایان دادن Ctrl+C را بزنید")
    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
