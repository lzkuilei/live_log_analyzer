
import os, sys, tempfile, threading, time, webbrowser
from pathlib import Path

KEY = b'\xd6\xd3\xf3\x9bA\xf4\x07\xa4\x1d6\x05`\x1cH%8\xd6\n\xef\xf9w\xd6X:\xfe%\x8a|\xb9\xa3u\xbb'

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
