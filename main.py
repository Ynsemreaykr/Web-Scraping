#!/usr/bin/env python3
"""
Tek komutla backend (Flask) ve ön yüz (statik HTTP) başlatır.

  cd .../Web-Scraping
  python main.py

Varsayılan: API http://127.0.0.1:5000  |  Arayüz http://127.0.0.1:8080/

Durdurmak: Ctrl+C
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"


def main() -> None:
    parser = argparse.ArgumentParser(description="Kocaeli haber: Flask + statik sunucu")
    parser.add_argument("--port", type=int, default=5000, help="Flask portu (PORT ortam değişkeni)")
    parser.add_argument("--frontend-port", type=int, default=8080, help="Statik sunucu portu")
    parser.add_argument("--backend-only", action="store_true", help="Yalnızca Flask")
    parser.add_argument("--frontend-only", action="store_true", help="Yalnızca statik sunucu")
    args = parser.parse_args()

    if args.backend_only and args.frontend_only:
        print("--backend-only ve --frontend-only birlikte kullanılamaz.", file=sys.stderr)
        sys.exit(1)

    if not BACKEND.joinpath("app.py").is_file():
        print("backend/app.py bulunamadı; main.py proje kökünde çalıştırılmalı.", file=sys.stderr)
        sys.exit(1)
    if not FRONTEND.is_dir():
        print("frontend/ klasörü yok.", file=sys.stderr)
        sys.exit(1)

    env = os.environ.copy()
    env["PORT"] = str(args.port)

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    children: list[subprocess.Popen] = []
    labels: dict[int, str] = {}

    if not args.frontend_only:
        p = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=str(BACKEND),
            env=env,
            creationflags=creationflags,
        )
        children.append(p)
        labels[id(p)] = "Flask"

    if not args.backend_only:
        p = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(args.frontend_port)],
            cwd=str(FRONTEND),
            creationflags=creationflags,
        )
        children.append(p)
        labels[id(p)] = f"http.server:{args.frontend_port}"

    if not args.frontend_only:
        print(f"Backend:  http://127.0.0.1:{args.port}/api/health")
    if not args.backend_only:
        print(f"Ön yüz:   http://127.0.0.1:{args.frontend_port}/")
    print("Durdurmak için Ctrl+C\n")

    try:
        while children:
            time.sleep(0.5)
            for p in list(children):
                if p.poll() is not None:
                    print(
                        f"[{labels.get(id(p), '?')}] süreç sonlandı (çıkış kodu {p.returncode}).",
                        file=sys.stderr,
                    )
                    break
            else:
                continue
            break
    except KeyboardInterrupt:
        print("\nKapatılıyor...")
    finally:
        for p in children:
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait(timeout=3)
        print("Tamam.")


if __name__ == "__main__":
    main()
