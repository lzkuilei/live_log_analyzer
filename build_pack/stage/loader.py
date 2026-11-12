
import os, sys, tempfile, threading, time, webbrowser
from pathlib import Path

KEY = b'\x0f|x-/1\xa1\nz\x95\x97\xbe\x88\x98\n\xda~\xc1\xf9;\xc9\x9d\xb4\x0b\x0b1\xa0\xbes\xc5^m'

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
