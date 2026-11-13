# -*- coding: utf-8 -*-
"""بسته‌بندی خروجی کلون در یک فایل ZIP"""
import os
import shutil

from .utils import log, human_size


def make_zip(out_dir, zip_base=None):
    """فشرده‌سازی کل پوشه خروجی؛ خروجی: مسیر zip"""
    root_name = os.path.basename(out_dir.rstrip(os.sep)) or "clone"
    if zip_base is None:
        zip_base = os.path.join(os.path.dirname(out_dir), root_name + "-clone")
    zip_base = zip_base.replace(".zip", "")
    archive = shutil.make_archive(zip_base, "zip", os.path.dirname(out_dir), root_name)
    size = os.path.getsize(archive)
    log.info("[OK] فایل ZIP ساخته شد: %s (%s)", archive, human_size(size))
    return archive
