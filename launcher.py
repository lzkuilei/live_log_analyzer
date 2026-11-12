# -*- coding: utf-8 -*-
"""exe 启动入口：启动 Streamlit 服务并自动打开浏览器。"""
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

def main():
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # PyInstaller 解包目录
    else:
        base = Path(__file__).parent

    app_path = base / "app.py"
    port = int(os.environ.get("PORT", "8501"))

    import streamlit.web.cli as stcli
    sys.argv = [
        "streamlit", "run", str(app_path),
        "--server.port", str(port),
        "--server.headless", "true",
        "--global.developmentMode", "false",
        "--browser.gatherUsageStats", "false",
    ]

    threading.Timer(3.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    stcli.main()


if __name__ == "__main__":
    main()
