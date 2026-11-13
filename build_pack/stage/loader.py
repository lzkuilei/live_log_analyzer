
import os, sys, tempfile, threading, time, webbrowser
from pathlib import Path

KEY = b'G\x9d\xb5GnLW\xbdD\x93\xfd\xc7(L\x80\xa1?3\xc4\x1aXziWb\xe9\xc4j\xc4\r\x1c\xe0'

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
    # 服务意外退出时自动重启（最多连续 5 次，避免死循环）
    restarts = 0
    while restarts < 5:
        try:
            stcli.main()
        except Exception as e:
            print("服务异常退出:", e)
        if restarts >= 4:
            break
        restarts += 1
        print(f"正在自动重启服务... (第 {restarts} 次)")
        time.sleep(2)

if __name__ == "__main__":
    main()
