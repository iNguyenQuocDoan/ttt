"""In print/sach.html ra PDF kho A5 bang Chrome headless.

Chay: python tools/print_pdf.py
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "print" / "sach.html"
OUTPUT = ROOT / "Tôi Tự Học (bản sửa font).pdf"

CANDIDATES = [
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
]


def find_browser():
    for name in ("chrome", "google-chrome", "chromium", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    for path in CANDIDATES:
        if path.exists():
            return str(path)
    raise SystemExit("Không tìm thấy Chrome hoặc Edge để in PDF.")


def main():
    browser = find_browser()
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "sach.pdf"
        subprocess.run([
            browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
            "--generate-pdf-document-outline",
            f"--user-data-dir={Path(tmp) / 'profile'}",
            f"--print-to-pdf={out}",
            SOURCE.as_uri(),
        ], check=True, capture_output=True, timeout=180)
        shutil.copyfile(out, OUTPUT)
    print("Đã in:", OUTPUT)


if __name__ == "__main__":
    main()
