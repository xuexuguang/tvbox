#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
饭太硬（JPEG + Base64 封装）本地提取脚本
优先读取 config/sources.json 中“饭太硬”的 urls 列表依次尝试，也支持命令行传入 URL。
"""
import base64
import json
import os
import re
import sys
import urllib.parse

import requests

from source_config import load_source_config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT, "config", "sources.json")
OUTPUT_DIR = "output" if os.environ.get("GITHUB_ACTIONS") == "true" else "output-local"
DEFAULT_OUT = os.environ.get("TVBOX_FTY_OUTPUT") or os.path.join(ROOT, OUTPUT_DIR, "fantaiying.json")

DEFAULT_URLS = [
    "http://www.xn--sss604efuw.net/tv",
]

HEADERS = {
    "User-Agent": "okhttp/4.12.0",
    "Accept": "*/*",
}


def idn_encode(url: str) -> str:
    """将 URL 中的中文域名转成 punycode。"""
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ""
    try:
        encoded_host = host.encode("idna").decode("ascii")
    except Exception:
        encoded_host = host
    netloc = encoded_host
    if parsed.port:
        netloc = f"{encoded_host}:{parsed.port}"
    return urllib.parse.urlunsplit(
        (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)
    )


def load_fty_urls_from_config() -> list[str]:
    """从 config/sources.json 读取饭太硬配置的 urls 列表。"""
    if not os.path.exists(CONFIG_FILE):
        return []
    try:
        cfg = load_source_config(CONFIG_FILE)
        for src in cfg.get("sources", []) or []:
            if not isinstance(src, dict):
                continue
            if src.get("id") == "fantaiying" or src.get("name") == "饭太硬":
                urls = src.get("urls") or []
                return [u for u in urls if isinstance(u, str) and u.strip()]
    except Exception:
        pass
    return []


def decode_fty_bytes(data: bytes) -> dict:
    eoi = data.rfind(b"\xff\xd9")
    if eoi == -1:
        raise ValueError("未找到 JPEG 结束标记 FFD9")

    payload = data[eoi + 2 :]
    if not payload:
        raise ValueError("JPEG 结束标记后无有效载荷")

    b64_str = re.sub(rb"[^A-Za-z0-9+/=]", b"", payload)
    b64_str += b"=" * ((4 - len(b64_str) % 4) % 4)
    raw = base64.b64decode(b64_str)

    text = raw.decode("utf-8", errors="replace").lstrip("\ufeff").strip()

    idx_spider = text.find('"spider"')
    idx_brace = text.find("{")
    if idx_spider != -1 and (idx_brace == -1 or idx_spider < idx_brace):
        body = text[idx_spider:].strip().rstrip(",")
        if not body.startswith("{"):
            body = "{\n" + body
        if not body.endswith("}"):
            body = body + "\n}"
        text = body
    elif idx_brace != -1:
        text = text[idx_brace:]
    else:
        raise ValueError("解码文本中未找到 JSON 起始位置")

    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("//")]
    cleaned = "\n".join(lines)
    cleaned = re.sub(r",\s*([\]}])", r"\1", cleaned)

    obj = json.loads(cleaned, strict=False)
    if not isinstance(obj, dict) or not any(k in obj for k in ("sites", "lives", "spider")):
        raise ValueError("解析结果不是合法的 TVBox 配置对象")
    return obj


def fetch_one(url: str, timeout: int = 15) -> dict:
    target = idn_encode(url)
    resp = requests.get(target, headers=HEADERS, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    return decode_fty_bytes(resp.content)


def main() -> int:
    urls = sys.argv[1:] or load_fty_urls_from_config() or DEFAULT_URLS
    last_err = None
    for u in urls:
        try:
            data = fetch_one(u)
            os.makedirs(os.path.dirname(DEFAULT_OUT), exist_ok=True)
            with open(DEFAULT_OUT, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(
                f"[OK] {u} -> {DEFAULT_OUT} "
                f"(sites={len(data.get('sites', []))}, lives={len(data.get('lives', []))})"
            )
            return 0
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"[FAIL] {u} -> {e}")
    print(f"全部失败：{last_err}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
