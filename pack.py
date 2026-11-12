# -*- coding: utf-8 -*-
"""打包脚本：源码混淆加密 + PyInstaller 单文件 exe。

用法：python pack.py
产物：dist/LiveLogAnalyzer/LiveLogAnalyzer.exe（onedir，启动更快）
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
BUILD = ROOT / "build_pack"

# 每次打包随机生成混淆密钥
KEY = os.urandom(32)


def obfuscate(data: bytes) -> bytes:
    return bytes(b ^ KEY[i % len(KEY)] for i, b in enumerate(data))


def header(data: bytes) -> bytes:
    return KEY[:4] + data  # 简单魔数前缀


def prepare() -> Path:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    stage = BUILD / "stage"
    (stage / "src").mkdir(parents=True)

    # 加密 app.py 与 src/*.py
    (stage / "app.enc").write_bytes(header(obfuscate((ROOT / "app.py").read_bytes())))
    for py in (ROOT / "src").glob("*.py"):
        (stage / "src" / f"{py.stem}.enc").write_bytes(header(obfuscate(py.read_bytes())))
    # .streamlit 主题配置
    shutil.copytree(ROOT / ".streamlit", stage / ".streamlit")

    # 解密加载器：运行时把加密文件还原到临时目录
    loader = r'''
import os, sys, tempfile, threading, time, webbrowser
from pathlib import Path

KEY = __KEY__

def _dec(blob: bytes) -> bytes:
    k = KEY
    body = blob[4:]
    return bytes(b ^ k[i % len(k)] for i, b in enumerate(body))

def _free_port(start):
    import socket
    port = start
    for _ in range(50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
        port += 1
    return port

def main():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    runtime = Path(tempfile.mkdtemp(prefix="lla_"))
    (runtime / "app.py").write_bytes(_dec((base / "app.enc").read_bytes()))
    (runtime / "src").mkdir()
    for enc in (base / "src").glob("*.enc"):
        (runtime / "src" / f"{enc.stem}.py").write_bytes(_dec(enc.read_bytes()))

    port = _free_port(int(os.environ.get("PORT", "8501")))
    import streamlit.web.cli as stcli
    sys.argv = ["streamlit", "run", str(runtime / "app.py"),
                "--server.port", str(port), "--server.headless", "true",
                "--global.developmentMode", "false",
                "--browser.gatherUsageStats", "false"]
    threading.Timer(3.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    print(f"服务端口: {port}（关闭本窗口即退出程序）")
    stcli.main()

if __name__ == "__main__":
    main()
'''.replace("__KEY__", repr(KEY))
    (stage / "loader.py").write_text(loader, encoding="utf-8")
    return stage


def build(stage: Path):
    name = "LiveLogAnalyzer"
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onedir", "--name", name,
        "--distpath", str(BUILD / "dist"),
        "--workpath", str(BUILD / "work"),
        "--specpath", str(BUILD),
        "--icon", str(ROOT / "icon.ico"),
        # 依赖收集
        "--collect-all", "streamlit",
        "--collect-all", "plotly",
        "--collect-all", "openpyxl",
        "--collect-all", "altair",
        # 数据文件
        "--add-data", f"{stage / 'app.enc'}{os.pathsep}.",
        "--add-data", f"{stage / 'src'}{os.pathsep}src",
        "--add-data", f"{stage / '.streamlit'}{os.pathsep}.streamlit",
        # 隐式导入
        "--hidden-import", "pandas",
        "--hidden-import", "matplotlib",
        "--hidden-import", "openpyxl",
        "--hidden-import", "fpdf2",
        str(stage / "loader.py"),
    ]
    subprocess.run(cmd, check=True)
    print(f"\n完成！exe 位置: {BUILD / 'dist' / name / (name + '.exe')}")


if __name__ == "__main__":
    stage = prepare()
    build(stage)
