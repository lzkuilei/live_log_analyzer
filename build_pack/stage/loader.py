
import os, sys, tempfile, threading, time, webbrowser
from pathlib import Path

KEY = b"Z\xc4\x8a\xfe\xdd[\xa7@_'\x81B\xfe\x90\xe5\xc7\x81'\x10\x87\xa8I\n\x06\xbf\xec\x9e~\xd6\x1a8T"

def _dec(blob: bytes) -> bytes:
    k = KEY
    body = blob[4:]
    return bytes(b ^ k[i % len(k)] for i, b in enumerate(body))

def main():
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    runtime = Path(tempfile.mkdtemp(prefix="lla_"))
    (runtime / "app.py").write_bytes(_dec((base / "app.enc").read_bytes()))
    (runtime / "src").mkdir()
    for enc in (base / "src").glob("*.enc"):
        (runtime / "src" / f"{enc.stem}.py").write_bytes(_dec(enc.read_bytes()))

    port = int(os.environ.get("PORT", "8501"))
    import streamlit.web.cli as stcli
    sys.argv = ["streamlit", "run", str(runtime / "app.py"),
                "--server.port", str(port), "--server.headless", "true",
                "--global.developmentMode", "false",
                "--browser.gatherUsageStats", "false"]
    threading.Timer(3.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    stcli.main()

if __name__ == "__main__":
    main()
