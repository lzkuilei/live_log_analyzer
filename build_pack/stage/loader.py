
import os, sys, tempfile, threading, time, webbrowser
from pathlib import Path

KEY = b"\xae\x7f{\\\x18>w\xcd\x18\xc1\xb2\xf6{\x9e[\xdb\xf6\xff\x14h\xdd\xbb\xf3 }\rG\x06_k'm"

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
