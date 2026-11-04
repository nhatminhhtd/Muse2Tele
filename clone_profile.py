"""Clone 1 profile FoxProfile qua REST: POST /api/v1/profiles/{nguon}/clone.

    python clone_profile.py <profile nguon> <ten moi> [--no-data] [--same-fingerprint] [--url http://127.0.0.1:8010]

Mac dinh chep du lieu trinh duyet (cookie, dang nhap, tab) va tao fingerprint moi. Doc FOXPROFILE_URL /
FOXPROFILE_API_TOKEN tu .env canh file nay neu co.
"""
import argparse
import os
import sys
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def main() -> int:
    ap = argparse.ArgumentParser(description="Clone profile FoxProfile")
    ap.add_argument("source")
    ap.add_argument("new_name")
    ap.add_argument("--no-data", action="store_true", help="chi chep cau hinh, khong chep cookie/dang nhap")
    ap.add_argument("--same-fingerprint", action="store_true", help="giu fingerprint cua profile nguon")
    ap.add_argument("--url", default=os.environ.get("FOXPROFILE_URL", "http://127.0.0.1:8010"))
    a = ap.parse_args()
    headers = {}
    if token := os.environ.get("FOXPROFILE_API_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(
        f"{a.url.rstrip('/')}/api/v1/profiles/{quote(a.source, safe='')}/clone",
        json={"name": a.new_name, "include_data": not a.no_data, "new_fingerprint": not a.same_fingerprint},
        headers=headers,
        timeout=1800,  # chep du lieu profile co the mat vai phut
    )
    if r.status_code != 201:
        print(f"Loi {r.status_code}: {r.json().get('detail', r.text) if r.content else ''}")
        return 1
    print(f"Da clone {a.source} -> {a.new_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
