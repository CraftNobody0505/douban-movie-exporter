#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export Douban book records (read / wish / reading) to CSV."""

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
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


BASE = "https://book.douban.com"
SCRIPT_DIR = Path(__file__).resolve().parent
COOKIE_FILE = SCRIPT_DIR / "douban_cookie.txt"
STATUS_LABELS = {"collect": "读过", "wish": "想读", "do": "在读"}


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\xa0", " ")
    return re.sub(r"\s+", " ", value).strip()


def attr(tag: str, name: str) -> str:
    for pattern in (rf'{re.escape(name)}="([^"]*)"', rf"{re.escape(name)}='([^']*)'"):
        match = re.search(pattern, tag, flags=re.I | re.S)
        if match:
            return html.unescape(match.group(1)).strip()
    return ""


def read_cookie(arg_cookie: str | None) -> str:
    if arg_cookie:
        return arg_cookie.strip()
    if os.environ.get("DOUBAN_COOKIE", "").strip():
        return os.environ["DOUBAN_COOKIE"].strip()
    if COOKIE_FILE.exists():
        return COOKIE_FILE.read_text(encoding="utf-8").strip()
    return ""


def fetch(url: str, cookie: str, user_id: str, timeout: int = 30) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": f"{BASE}/people/{user_id}/",
        "Connection": "close",
    }
    if cookie:
        headers["Cookie"] = cookie
    with urlopen(Request(url, headers=headers), timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def looks_blocked(page_html: str) -> bool:
    return any(
        hint in page_html
        for hint in (
            "检测到有异常请求",
            "sec.douban.com",
            "403 Forbidden",
            "<title>禁止访问</title>",
        )
    )


def split_items(page_html: str) -> list[str]:
    starts = [
        match.start()
        for match in re.finditer(
            r'<li\s+class="[^"]*\bsubject-item\b[^"]*"[^>]*>',
            page_html,
            flags=re.I | re.S,
        )
    ]
    blocks: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(page_html)
        block = page_html[start:end]
        if "/subject/" in block:
            blocks.append(block)
    return blocks


def parse_pub_info(pub_info: str) -> tuple[str, str, str, str]:
    parts = [part.strip() for part in pub_info.split(" / ") if part.strip()]
    publication_date = ""
    date_index = -1
    for index in range(len(parts) - 1, -1, -1):
        if re.match(r"^\d{4}(?:-\d{1,2})?(?:-\d{1,2})?$", parts[index]):
            publication_date = parts[index]
            date_index = index
            break

    price = ""
    if date_index >= 0 and date_index + 1 < len(parts):
        price = " / ".join(parts[date_index + 1 :])

    publisher = parts[date_index - 1] if date_index > 0 else ""
    authors = " / ".join(parts[: date_index - 1]) if date_index > 1 else ""
    return authors, publisher, publication_date, price


def parse_item(block: str, status: str) -> dict[str, str]:
    title_match = re.search(
        r'<h2[^>]*>.*?<a([^>]*)>(.*?)</a>', block, flags=re.I | re.S
    )
    title = ""
    link = ""
    if title_match:
        title = attr(title_match.group(1), "title") or clean_text(title_match.group(2))
        link = attr(title_match.group(1), "href")

    subject_match = re.search(r"/subject/(\d+)/", link)
    subject_id = subject_match.group(1) if subject_match else ""

    cover_match = re.search(r'<div[^>]+class="pic"[^>]*>.*?<img([^>]*)>', block, re.I | re.S)
    cover = attr(cover_match.group(1), "src") if cover_match else ""

    pub_match = re.search(r'<div[^>]+class="pub"[^>]*>(.*?)</div>', block, re.I | re.S)
    pub_info = clean_text(pub_match.group(1)) if pub_match else ""
    authors, publisher, publication_date, price = parse_pub_info(pub_info)

    rating_match = re.search(r'<span[^>]+class="[^"]*rating(\d)-t[^"]*"', block, re.I)
    rating = rating_match.group(1) if rating_match else ""

    date_match = re.search(r'<span[^>]+class="date"[^>]*>(.*?)</span>', block, re.I | re.S)
    date_text = clean_text(date_match.group(1)) if date_match else ""
    marked_match = re.search(r"\d{4}-\d{2}-\d{2}", date_text)
    marked_date = marked_match.group(0).replace("-", "/") if marked_match else ""

    comment_match = re.search(
        r'<p[^>]+class="[^"]*\bcomment\b[^"]*"[^>]*>(.*?)</p>',
        block,
        re.I | re.S,
    )
    comment = clean_text(comment_match.group(1)) if comment_match else ""

    tags_match = re.search(r'<span[^>]+class="tags"[^>]*>(.*?)</span>', block, re.I | re.S)
    tags = clean_text(tags_match.group(1)).removeprefix("标签:").strip() if tags_match else ""

    return {
        "status": status,
        "status_label": STATUS_LABELS[status],
        "title": title,
        "rating": rating,
        "marked_date": marked_date,
        "comment": comment,
        "authors": authors,
        "publisher": publisher,
        "publication_date": publication_date,
        "price": price,
        "pub_info": pub_info,
        "tags": tags,
        "link": link,
        "subject_id": subject_id,
        "cover": cover,
    }


def find_next_url(page_html: str, current_url: str) -> str:
    paginator = re.search(r'<div\s+class="paginator"\s*>(.*?)</div>', page_html, re.I | re.S)
    if not paginator:
        return ""
    match = re.search(
        r'<span[^>]+class="next"[^>]*>.*?<a[^>]+href="([^"]+)"',
        paginator.group(1),
        re.I | re.S,
    )
    if not match:
        return ""
    next_url = urljoin(current_url, html.unescape(match.group(1)))
    return next_url if "/people/" in next_url else ""


def scrape_status(
    user_id: str,
    status: str,
    cookie: str,
    delay: float,
    retries: int,
) -> list[dict[str, str]]:
    url = (
        f"{BASE}/people/{user_id}/{status}"
        "?start=0&sort=time&rating=all&filter=all&mode=grid"
    )
    rows: list[dict[str, str]] = []
    page_no = 0

    while url:
        page_no += 1
        print(f"[{status}] fetching page {page_no}: {url}")
        page_html = ""
        for attempt in range(1, retries + 1):
            page_html = fetch(url, cookie, user_id)
            if not looks_blocked(page_html):
                break
            if attempt == retries:
                raise RuntimeError("Douban returned a security page repeatedly.")
            wait = 120 * attempt
            print(f"  security page, waiting {wait}s before retry")
            time.sleep(wait)

        blocks = split_items(page_html)
        print(f"  found {len(blocks)} books")
        if not blocks:
            break
        rows.extend(parse_item(block, status) for block in blocks)
        url = find_next_url(page_html, url)
        if url:
            time.sleep(delay + random.uniform(0, 1.5))

    return rows


def write_csv(rows: list[dict[str, str]], user_id: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = SCRIPT_DIR / f"douban_books_{user_id}_all_{stamp}.csv"
    fields = [
        "status", "status_label", "title", "rating", "marked_date", "comment",
        "authors", "publisher", "publication_date", "price", "pub_info", "tags",
        "link", "subject_id", "cover",
    ]
    with output.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Douban book records to CSV.")
    parser.add_argument("--user", required=True, help="Douban user id")
    parser.add_argument(
        "--status", choices=["collect", "wish", "do", "all"], default="all"
    )
    parser.add_argument("--cookie", default="")
    parser.add_argument("--delay", type=float, default=12.0)
    parser.add_argument("--retries", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cookie = read_cookie(args.cookie)
    statuses = ["collect", "wish", "do"] if args.status == "all" else [args.status]
    rows: list[dict[str, str]] = []
    try:
        for status in statuses:
            rows.extend(scrape_status(args.user, status, cookie, args.delay, args.retries))
    except HTTPError as error:
        print(f"HTTP error: {error.code} {error.reason}", file=sys.stderr)
        return 2
    except (URLError, TimeoutError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    output = write_csv(rows, args.user)
    print(f"\nDone. Exported {len(rows)} books:\n{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
