#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Export Douban movie collection pages to CSV.

Examples:
  py douban_movie_export.py --user YOUR_DOUBAN_ID
  py douban_movie_export.py --user YOUR_DOUBAN_ID --status all
  py douban_movie_export.py --user YOUR_DOUBAN_ID --cookie "YOUR_COOKIE"

If Douban returns 403 or shows a security/login page, create a file named
douban_cookie.txt next to this script and paste your browser Cookie into it.

Supported status:
  collect  watched
  wish     wish list
  do       watching
  all      all three above
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


BASE = "https://movie.douban.com"
SCRIPT_DIR = Path(__file__).resolve().parent
COOKIE_FILE = SCRIPT_DIR / "douban_cookie.txt"

STATUS_LABELS = {
    "collect": "看过",
    "wish": "想看",
    "do": "在看",
}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\xa0", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def attr(tag: str, name: str) -> str:
    for pattern in (rf'{re.escape(name)}="([^"]*)"', rf"{re.escape(name)}='([^']*)'"):
        match = re.search(pattern, tag, flags=re.I | re.S)
        if match:
            return html.unescape(match.group(1)).strip()
    return ""


def read_cookie(arg_cookie: str | None) -> str:
    if arg_cookie:
        return arg_cookie.strip()
    env_cookie = os.environ.get("DOUBAN_COOKIE", "").strip()
    if env_cookie:
        return env_cookie
    if COOKIE_FILE.exists():
        return COOKIE_FILE.read_text(encoding="utf-8").strip()
    return ""


def fetch(url: str, cookie: str, user_id: str, timeout: int = 30) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": f"{BASE}/people/{user_id}/",
        "Connection": "close",
    }
    if cookie:
        headers["Cookie"] = cookie

    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def split_items(page_html: str) -> list[str]:
    grid_match = re.search(
        r'<div\s+class="grid-view"\s*>(.*?)(?:<div\s+class="paginator"|</div>\s*</div>\s*</div>\s*</div>)',
        page_html,
        flags=re.I | re.S,
    )
    grid_html = grid_match.group(1) if grid_match else page_html
    starts = [
        match.start()
        for match in re.finditer(
            r'<div\s+class="[^"]*\bitem\b[^"]*"[^>]*>',
            grid_html,
            flags=re.I | re.S,
        )
    ]
    blocks: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(grid_html)
        block = grid_html[start:end]
        if "class=\"title\"" in block or "class='title'" in block:
            blocks.append(block)
    return blocks


def parse_rating(block: str) -> str:
    match = re.search(r'<span[^>]+class="[^"]*rating(\d)-t[^"]*"[^>]*>', block, flags=re.I)
    return match.group(1) if match else ""


def parse_date(block: str) -> str:
    match = re.search(r'<span[^>]+class="date"[^>]*>(.*?)</span>', block, flags=re.I | re.S)
    return clean_text(match.group(1)).replace("-", "/") if match else ""


def parse_comment(block: str) -> str:
    match = re.search(r'<span[^>]+class="comment"[^>]*>(.*?)</span>', block, flags=re.I | re.S)
    return clean_text(match.group(1)) if match else ""


def parse_title_link(block: str) -> tuple[str, str, str]:
    title_match = re.search(
        r'<li[^>]+class="title"[^>]*>\s*<a([^>]*)>(.*?)</a>',
        block,
        flags=re.I | re.S,
    )
    if not title_match:
        return "", "", ""
    link = attr(title_match.group(1), "href")
    title = clean_text(title_match.group(2))
    subject_match = re.search(r"/subject/(\d+)/", link)
    subject_id = subject_match.group(1) if subject_match else ""
    return title, link, subject_id


def parse_cover(block: str) -> str:
    pic_match = re.search(r'<div[^>]+class="pic"[^>]*>.*?<img([^>]*)>', block, flags=re.I | re.S)
    if not pic_match:
        return ""
    cover = attr(pic_match.group(1), "src")
    if cover.endswith(".webp"):
        cover = cover[:-5] + ".jpg"
    return cover


def parse_intro(block: str) -> tuple[str, str, str]:
    match = re.search(r'<li[^>]+class="intro"[^>]*>(.*?)</li>', block, flags=re.I | re.S)
    intro = clean_text(match.group(1)) if match else ""
    release_date = ""
    country = ""
    first = intro.split(" / ")[0].strip() if intro else ""
    parsed = re.match(r"^(\d{4}-\d{2}-\d{2})\((.*?)\)$", first)
    if parsed:
        release_date = parsed.group(1).replace("-", "/")
        country = parsed.group(2)
    return intro, release_date, country


def parse_item(block: str, status: str) -> dict[str, str]:
    title, link, subject_id = parse_title_link(block)
    intro, release_date, country = parse_intro(block)
    return {
        "status": status,
        "status_label": STATUS_LABELS.get(status, status),
        "title": title,
        "rating": parse_rating(block),
        "rating_date": parse_date(block),
        "comment": parse_comment(block),
        "release_date": release_date,
        "country": country,
        "intro": intro,
        "link": link,
        "subject_id": subject_id,
        "cover": parse_cover(block),
    }


def find_next_url(page_html: str, current_url: str) -> str:
    paginator = re.search(r'<div\s+class="paginator"\s*>(.*?)</div>', page_html, flags=re.I | re.S)
    if not paginator:
        return ""
    match = re.search(
        r'<span[^>]+class="next"[^>]*>.*?<a[^>]+href="([^"]+)"',
        paginator.group(1),
        flags=re.I | re.S,
    )
    if not match:
        return ""
    next_url = urljoin(current_url, html.unescape(match.group(1)))
    return next_url if "/people/" in next_url else ""


def looks_blocked(page_html: str) -> bool:
    return any(
        hint in page_html
        for hint in (
            "检测到有异常请求",
            "sec.douban.com",
            "403 Forbidden",
        )
    )


def scrape_status(
    user_id: str,
    status: str,
    cookie: str,
    delay: float,
    max_pages: int,
    start: int = 0,
    retries: int = 3,
) -> list[dict[str, str]]:
    url = (
        f"{BASE}/people/{user_id}/{status}"
        f"?start={start}&sort=time&rating=all&filter=all&mode=grid"
    )
    page_no = 0
    rows: list[dict[str, str]] = []

    while url:
        page_no += 1
        print(f"[{status}] fetching page {page_no}: {url}")
        page_html = ""
        for attempt in range(1, retries + 1):
            page_html = fetch(url, cookie, user_id)
            if not looks_blocked(page_html):
                break
            if attempt >= retries:
                raise RuntimeError(
                    "Douban returned a login/security page repeatedly. "
                    "Wait a while, then retry with --start set to the last printed start value."
                )
            wait = 60 * attempt
            print(f"  got security page, waiting {wait}s before retry {attempt + 1}/{retries}")
            time.sleep(wait)

        blocks = split_items(page_html)
        print(f"  found {len(blocks)} items")
        if not blocks:
            break
        rows.extend(parse_item(block, status) for block in blocks)

        if max_pages and page_no >= max_pages:
            break
        next_url = find_next_url(page_html, url)
        if not next_url:
            break
        url = next_url
        time.sleep(delay + random.uniform(0.0, 1.5))

    return rows


def write_csv(rows: Iterable[dict[str, str]], user_id: str, status_name: str, output_dir: Path) -> Path:
    rows = list(rows)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = output_dir / f"douban_movie_{user_id}_{status_name}_{stamp}.csv"
    fields = [
        "status",
        "status_label",
        "title",
        "rating",
        "rating_date",
        "comment",
        "release_date",
        "country",
        "intro",
        "link",
        "subject_id",
        "cover",
    ]
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Douban movie collection to CSV.")
    parser.add_argument("--user", required=True, help="Douban numeric/user id")
    parser.add_argument(
        "--status",
        default="collect",
        choices=["collect", "wish", "do", "all"],
        help="collect=watched, wish=wish list, do=watching, all=all three",
    )
    parser.add_argument("--cookie", default="", help="Douban Cookie string")
    parser.add_argument("--delay", type=float, default=6.0, help="Delay between pages in seconds")
    parser.add_argument("--max-pages", type=int, default=0, help="Debug limit. 0 means no limit")
    parser.add_argument("--start", type=int, default=0, help="Start offset, e.g. 465 resumes from page 32")
    parser.add_argument("--retries", type=int, default=3, help="Retries for login/security pages")
    parser.add_argument("--output-dir", default=str(SCRIPT_DIR), help="CSV output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cookie = read_cookie(args.cookie)
    statuses = ["collect", "wish", "do"] if args.status == "all" else [args.status]
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict[str, str]] = []
    try:
        for status in statuses:
            all_rows.extend(
                scrape_status(
                    user_id=args.user,
                    status=status,
                    cookie=cookie,
                    delay=args.delay,
                    max_pages=args.max_pages,
                    start=args.start,
                    retries=args.retries,
                )
            )
    except HTTPError as exc:
        print(f"\nHTTP error: {exc.code} {exc.reason}", file=sys.stderr)
        if exc.code in (403, 418):
            print(
                "Douban blocked anonymous/script access. "
                f"Put your browser Cookie into {COOKIE_FILE} and retry.",
                file=sys.stderr,
            )
        return 2
    except (URLError, TimeoutError, RuntimeError) as exc:
        print(f"\nError: {exc}", file=sys.stderr)
        return 2

    out = write_csv(all_rows, args.user, args.status, output_dir)
    print(f"\nDone. Exported {len(all_rows)} rows:")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
