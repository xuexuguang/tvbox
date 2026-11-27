#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
影视仓 / TVBox 配置自动更新脚本
=================================
功能：
  1. 读取 config/sources.json 中的配置源列表，限量并发抓取常规源
  2. 对每个源依次尝试"主线 + 备用"多个地址，自动做中文域名 punycode 转换
  3. 校验返回内容是否为合法的 TVBox/影视仓 单仓配置（包含 sites/spiders/lives 等字段）
     或 多仓订阅（顶层含 urls 数组）
  4. 再按特殊源处理（调用 tsjm.py 提取饭太硬 JPEG+Base64 配置；
     若当前网络如 GitHub Actions 海外节点抓取失败，自动回退使用本地 output/fantaiying.json 缓存），
     并将饭太硬排在多仓订阅与单仓聚合的首位
  5. 将每个源的最新配置保存到 output/<id>.json
  6. 生成多仓订阅文件 output/多仓订阅.json（可直接填进影视仓的"订阅"或"多仓"）
  7. 生成聚合单仓 output/单仓聚合.json（所有源 sites/lives/parses 合并去重）
  8. 生成 shields 徽章。上述产物在本地运行时写入 outout_local/
兼容：本脚本同时兼容 GitHub Actions 自动运行 与 本地手动运行。
在 GitHub Actions 中，环境变量 GITHUB_REPOSITORY 会被自动注入（格式 owner/repo），
用于拼出多仓订阅里指向本仓库 raw 文件的完整 URL。
用法：
  python scripts/update.py
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import requests

from source_config import load_source_config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT, "config", "sources.json")
IS_GITHUB_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"
OUTPUT_DIR = os.path.join(ROOT, "output" if IS_GITHUB_ACTIONS else "outout_local")
CACHE_DIR = os.path.join(ROOT if IS_GITHUB_ACTIONS else OUTPUT_DIR, "source-cache")
FTY_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tsjm.py")

DEFAULT_REPO = "xuexuguang/tvbox"

# 模拟 TVBox / 影视仓 客户端请求头
USER_AGENT = "okhttp/4.12.0"

TIMEOUT = 15  # 单个地址超时（秒）
MAX_RETRIES = 2  # 单个地址最大尝试次数（仅对超时/连接类瞬态错误重试）
RETRY_BACKOFF = 2  # 重试基础等待秒数
URL_INTERVAL = 1.0  # 每个地址之间的小间隔秒数（降低被限流概率）
MAX_WORKERS = 4

# 判定"像 TVBox 单仓配置"的顶层字段
TVBOX_KEYS = ("sites", "spiders", "lives", "store", "exts", "parses", "flags")
# 多仓订阅格式：顶层为 urls 数组
MULTI_KEYS = ("urls", "订阅")


def _strip_js_comments(text: str) -> str:
    """剔除 JSON 中内嵌的 // 行注释（部分接口会在字段后追加免责注释）。"""
    lines = text.split("\n")
    cleaned = [ln for ln in lines if not ln.lstrip().startswith("//")]
    return "\n".join(cleaned)


def parse_json_lenient(text: str):
    """宽容解析：去 BOM/空白、剔 // 注释后优先整体 json.loads；
    若接口返回了拼接的多段 JSON，取第一段有效对象。"""
    text = text.lstrip("\ufeff").strip()
    text = _strip_js_comments(text)
    try:
        # strict=False 允许字符串中出现未转义的控制字符（部分接口的 JSON 不规范）
        return json.loads(text, strict=False)
    except json.JSONDecodeError:
        # 兼容"返回了多个 JSON 拼接在一起"的接口
        decoder = json.JSONDecoder(strict=False)
        try:
            obj, _ = decoder.raw_decode(text)
            return obj
        except Exception:
            raise


def idn_encode(url: str) -> str:
    """将 URL 中的中文（国际化）域名转成 punycode，避免 DNS 解析失败。
    例如：http://www.饭太硬.com/tv -> http://www.xn--sss604efuw.com/tv
    """
    parsed = urllib.parse.urlsplit(url)
    host = parsed.hostname or ""
    try:
        encoded_host = host.encode("idna").decode("ascii")
    except Exception:
        encoded_host = host  # 已是 ascii 或转换失败，原样使用
    netloc = encoded_host
    if parsed.port:
        netloc = f"{encoded_host}:{parsed.port}"
    return urllib.parse.urlunsplit(
        (parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment)
    )


def is_valid_tvbox_config(data) -> bool:
    """粗略校验：返回内容是否像 TVBox/影视仓 配置（单仓或多仓订阅）。"""
    if not isinstance(data, dict):
        return False
    if any(key in data for key in TVBOX_KEYS):
        return True
    # 多仓订阅格式：{"urls": [{"name":..., "url":...}, ...]}
    if "urls" in data and isinstance(data.get("urls"), list) and data["urls"]:
        return True
    return False


def _should_retry(err: Exception, resp_text_len: int = -1) -> bool:
    """判断失败是否值得重试：
    - 超时/连接类瞬态错误：重试
    - 空响应 / JSON 解析失败（疑似服务端反爬冷却）：重试（加长等待）
    - 4xx/5xx、返回了内容但结构不对（确定性失败）：不重试
    """
    if isinstance(err, (requests.exceptions.Timeout, requests.exceptions.ConnectionError)):
        return True
    if isinstance(err, requests.exceptions.HTTPError):
        return False  # 4xx/5xx 为确定性失败
    if isinstance(err, json.JSONDecodeError):
        return True  # 空响应或非 JSON，可能是反爬/冷却，给一次机会
    if resp_text_len <= 0:
        return True  # 没有拿到任何内容
    return False


def cms_config(source, url, response):
    try:
        data = response.json()
    except ValueError:
        try:
            entries = ET.fromstring(response.content).findall(".//video")
        except ET.ParseError as error:
            raise ValueError("采集接口未返回有效片单") from error
    else:
        entries = data.get("list") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise ValueError("采集接口未返回有效片单")
    return {"sites": [{
        "key": source["id"], "name": source["name"], "type": 3,
        "api": url, "searchable": 1, "quickSearch": 1, "filterable": 1,
    }]}


def fetch_config(url: str, cms_source=None) -> tuple[dict, str, int]:
    """返回配置、重定向后的地址和成功请求的耗时（毫秒）。"""
    target = idn_encode(url)
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            started = time.perf_counter()
            resp = requests.get(
                target,
                params={"ac": "list", "pg": 1} if cms_source else None,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json,text/plain,*/*",
                },
                timeout=TIMEOUT,
                allow_redirects=True,
            )
            request_ms = round((time.perf_counter() - started) * 1000)
            resp.raise_for_status()
            if cms_source:
                return cms_config(cms_source, url, resp), url, request_ms
            data = parse_json_lenient(resp.text)
            if not is_valid_tvbox_config(data):
                raise ValueError("返回内容不是 TVBox 配置（缺少 sites/spiders/lives 或 urls 字段）")
            return data, resp.url, request_ms
        except Exception as e:  # noqa: BLE001
            last_err = e
            text_len = len(getattr(resp, "text", "") or "") if "resp" in locals() else -1
            if _should_retry(e, text_len) and attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF * attempt * 2
                print(f"      (第 {attempt} 次失败：{e}，{wait}s 后重试)")
                time.sleep(wait)
            else:
                break
    raise last_err


def run_fantaiying(raw_base: str):
    """运行 tsjm.py 抓取饭太硬；失败时回退读取本地 output/fantaiying.json 缓存。
    返回: (entry_dict, sub_dict_or_None, fetched_tuple_or_None)
    """
    sid = "fantaiying"
    name = "饭太硬"
    out_path = os.path.join(OUTPUT_DIR, f"{sid}.json")
    entry = {"id": sid, "name": name, "ok": False, "used_url": None, "error": None}

    fetched_ok = False
    err_msg = None
    if os.path.exists(FTY_SCRIPT):
        try:
            res = subprocess.run(
                [sys.executable, FTY_SCRIPT],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "TVBOX_FTY_OUTPUT": os.path.join(CACHE_DIR, "fantaiying-jpeg.json")},
            )
            if res.returncode == 0:
                fetched_ok = True
                if res.stdout.strip():
                    print(res.stdout.strip())
            else:
                err_msg = (res.stdout or res.stderr or "tsjm.py 返回非 0").strip().splitlines()[-1]
                print(f"[WARN] {name} 实时抓取未成功（{err_msg}），尝试读取本地缓存...")
        except Exception as e:  # noqa: BLE001
            err_msg = str(e)
            print(f"[WARN] {name} 脚本执行异常（{err_msg}），尝试读取本地缓存...")
    else:
        err_msg = "未找到 scripts/tsjm.py"

    cached_path = os.path.join(CACHE_DIR, "fantaiying-jpeg.json")
    if os.path.exists(cached_path):
        out_path = cached_path
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if is_valid_tvbox_config(data):
                entry["ok"] = True
                if fetched_ok:
                    summary = res.stdout.strip().splitlines()[-1]
                    origin = summary.removeprefix("[OK] ").partition(" -> ")[0]
                    entry["used_url"] = f"{origin} (JPEG解包)"
                    entry["request_ms"] = int(summary.rpartition("request_ms=")[2])
                else:
                    entry["cached"] = True
                    entry["used_url"] = "(缓存)"
                    print(f"[CACHE] {name}  使用上次本地提取缓存")
                sub = {"name": name, "url": f"{raw_base}/{sid}.json"}
                return entry, sub, (sid, name, data)
        except Exception as e:  # noqa: BLE001
            err_msg = f"缓存读取失败: {e}"

    entry["error"] = err_msg or "抓取失败且无可用缓存"
    print(f"[FAIL] {name}  {entry['error']}")
    return entry, None, None


def _merge_list(fetched, field):
    """合并各源中的列表字段（lives/parses/doh 等），按 name/url 去重。"""
    seen = set()
    out = []
    for _sid, _name, data in fetched:
        for item in data.get(field, []) or []:
            if isinstance(item, dict):
                ident = item.get("name") or item.get("url") or json.dumps(
                    item, ensure_ascii=False, sort_keys=True
                )
            else:
                ident = str(item)
            if ident in seen:
                continue
            seen.add(ident)
            out.append(item)
    return out


def merge_configs(fetched):
    """把多个单仓配置合并成一个聚合单仓：
    - 以第一个成功源为基底（保留 spider/logo/wallpaper 等）
    - sites 按 key 去重，重复 key 加源 id 前缀
    - lives/parses/doh/rules/flags/exts 等列表合并去重
    fetched: [(sid, name, data_dict), ...]
    """
    if not fetched:
        return None
    _base_sid, base_name, base = fetched[0]
    merged = {}
    skip = {"sites", "lives", "parses", "doh", "rules", "flags", "exts", "ads", "urls"}
    for k, v in base.items():
        if k not in skip:
            merged[k] = v
    merged["warningText"] = (
        f"本配置由 {len(fetched)} 个公开源自动聚合（含{base_name}等），仅供学习交流，请勿商用"
    )

    seen_keys = set()
    sites = []
    for sid, _name, data in fetched:
        for s in data.get("sites", []) or []:
            if not isinstance(s, dict):
                continue
            key = s.get("key")
            if key is None:
                key = json.dumps(s, ensure_ascii=False, sort_keys=True)
            new_key = key
            if key in seen_keys:
                new_key = f"{sid}_{key}"
            if new_key in seen_keys:
                continue
            seen_keys.add(new_key)
            if new_key != key:
                s = dict(s)
                s["key"] = new_key
            sites.append(s)
    merged["sites"] = sites

    for field in ("lives", "parses", "doh", "rules", "flags", "exts"):
        merged[field] = _merge_list(fetched, field)

    return merged


def write_badge(ok_count, total):
    """生成 shields.io endpoint 徽章 JSON。"""
    if total == 0 or ok_count == 0:
        color = "red"
    elif ok_count < total:
        color = "orange"
    else:
        color = "green"
    badge = {
        "schemaVersion": 1,
        "label": "TVBox 配置",
        "message": f"{ok_count}/{total} 可用",
        "color": color,
    }
    with open(os.path.join(OUTPUT_DIR, "shield.json"), "w", encoding="utf-8") as f:
        json.dump(badge, f, ensure_ascii=False, indent=2)


def write_config(path, data):
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=os.path.dirname(path), delete=False
    ) as file:
        try:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.close()
            os.replace(file.name, path)
        finally:
            if os.path.exists(file.name):
                os.unlink(file.name)


def load_site_filter(config):
    path = os.path.join(os.path.dirname(CONFIG_FILE), "site_filter.jsonc")
    try:
        rules = load_source_config(path)
    except FileNotFoundError:
        rules = config.get("site_filter", {})
    except (OSError, ValueError) as error:
        raise ValueError(f"无法读取 {path}：{error}") from error
    if not isinstance(rules, dict) or rules.keys() - {"exclude_keys", "exclude_names"}:
        raise ValueError("site_filter 只支持 exclude_keys 和 exclude_names")
    exclusions = {}
    for field in ("key", "name"):
        values = rules.get(f"exclude_{field}s", [])
        if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
            raise ValueError(f"site_filter.exclude_{field}s 必须是字符串数组")
        exclusions[field] = set(values)
    return exclusions


def publish_config(sid, data, origin, raw_base, exclusions, ancestors=frozenset()):
    published = dict(data)
    if isinstance(data.get("sites"), list):
        published["sites"] = [
            site for site in data["sites"]
            if not isinstance(site, dict) or not any(
                isinstance(site.get(field), str) and site[field] in blocked
                for field, blocked in exclusions.items()
            )
        ]

    if ancestors:
        resource_fields = {"api", "ext", "spider", "url", "wallpaper", "logo", "jar"}

        def resolve_resources(value):
            if isinstance(value, list):
                return [resolve_resources(item) for item in value]
            if isinstance(value, dict):
                return {
                    key: urllib.parse.urljoin(origin, item)
                    if key in resource_fields and isinstance(item, str)
                    and item.startswith(("./", "../", "/"))
                    else resolve_resources(item)
                    for key, item in value.items()
                }
            return value

        published = resolve_resources(published)

    warehouses = []
    if any(exclusions.values()) and isinstance(data.get("urls"), list):
        published["urls"] = []
        ancestors = ancestors | {origin}
        for entry in data["urls"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("url"), str):
                continue
            url = urllib.parse.urljoin(origin, entry["url"])
            if urllib.parse.urlsplit(url).scheme not in {"http", "https"} or url in ancestors:
                continue
            child_id = "warehouse-" + hashlib.sha256(url.encode()).hexdigest()
            try:
                child, child_origin, _ = load_source(child_id, [url])
                if child_origin in ancestors:
                    continue
                name = entry.get("name") or url
                _, leaves = publish_config(child_id, child, child_origin, raw_base, exclusions, ancestors)
                if leaves:
                    published["urls"].extend(leaves)
                    warehouses.extend(leaves)
                elif any(field in child for field in TVBOX_KEYS):
                    link = {"name": name, "url": f"{raw_base}/{child_id}.json"}
                    published["urls"].append(link)
                    warehouses.append(link)
            except (OSError, ValueError, requests.RequestException) as error:
                print(f"[WARN] 子仓 {url} -> {error}")
        if not warehouses and not any(field in data for field in TVBOX_KEYS):
            raise ValueError("没有可发布的子仓")

    write_config(os.path.join(OUTPUT_DIR, f"{sid}.json"), published)
    return published, warehouses


def load_source(sid, urls, cms_source=None):
    cache_path = os.path.join(CACHE_DIR, f"{sid}.json")
    last_error = "没有配置地址"
    for url in urls:
        try:
            data, origin, request_ms = fetch_config(url, cms_source)
            write_config(cache_path, {"origin": origin, "data": data})
            return data, origin, request_ms
        except (OSError, ValueError, requests.RequestException) as error:
            print(f"[FAIL] {sid}  {url}  ->  {error}")
            last_error = str(error)
            time.sleep(URL_INTERVAL)

    try:
        with open(cache_path, encoding="utf-8") as file:
            cached = json.load(file)
        if is_valid_tvbox_config(cached["data"]):
            return cached["data"], cached["origin"], None
    except (OSError, ValueError, KeyError, TypeError):
        pass

    try:
        with open(os.path.join(OUTPUT_DIR, f"{sid}.json"), encoding="utf-8") as file:
            cached = json.load(file)
        if is_valid_tvbox_config(cached):
            return cached, next(iter(urls), ""), None
    except (OSError, ValueError):
        pass
    raise ValueError(last_error)


def update_source(source, raw_base, exclusions):
    name = source.get("name", "未知")
    sid = source.get("id", name)
    entry = {"id": sid, "name": name, "ok": False, "used_url": None, "error": None}
    try:
        cms_source = source if source.get("type") == "cms" else None
        data, origin, request_ms = load_source(sid, source.get("urls", []), cms_source)
        data, warehouses = publish_config(sid, data, origin, raw_base, exclusions)
        cached = request_ms is None
        if cached:
            entry["cached"] = True
        else:
            entry["request_ms"] = request_ms
        entry.update(ok=True, used_url="(缓存)" if cached else origin)
        print(f"[{'CACHE' if cached else 'OK'}] {name} <- {entry['used_url']}")
        return entry, data, warehouses
    except (ValueError, OSError) as error:
        entry["error"] = str(error)
        print(f"[FAIL] {name}  {error}")
        return entry, None, []


def main() -> int:
    cfg = load_source_config(CONFIG_FILE)

    try:
        exclusions = load_site_filter(cfg)
    except ValueError as error:
        print(f"[FAIL] {error}", file=sys.stderr)
        return 1

    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 东八区时间，便于阅读
    tz = datetime.timezone(datetime.timedelta(hours=8))
    now_str = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    # GitHub Actions 中自动注入 GITHUB_REPOSITORY=owner/repo
    repo = (
        os.environ.get("GITHUB_REPOSITORY")
        or os.environ.get("REPO")
        or DEFAULT_REPO
    )
    raw_base = f"https://gh-proxy.org/https://raw.githubusercontent.com/{repo}/main/output"

    status = {"updated_at": now_str, "repo": repo, "sources": []}
    subscriptions = []
    fetched = []  # [(sid, name, data_dict), ...] 用于聚合单仓

    sources_list = cfg.get("sources", [])
    regular_sources = [source for source in sources_list if source.get("id") != "fantaiying"]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for entry, data, warehouses in executor.map(
            lambda source: update_source(source, raw_base, exclusions), regular_sources
        ):
            status["sources"].append(entry)
            if entry["ok"]:
                sid, name = entry["id"], entry["name"]
                if not warehouses or any(field in data for field in TVBOX_KEYS):
                    subscriptions.append({"name": name, "url": f"{raw_base}/{sid}.json"})
                subscriptions.extend(warehouses)
                fetched.append((sid, name, data))

    # 2. 再按特殊源处理（如饭太硬：先跑 tsjm.py，失败回退本地缓存，并覆盖常规源里的同名项，排在首位）
    fty_entry, fty_sub, fty_fetched = run_fantaiying(raw_base)
    fty_warehouses = []
    if fty_entry["ok"]:
        sid, name, data = fty_fetched
        fty_source = next((source for source in sources_list if source.get("id") == sid), {})
        origin = next(iter(fty_source.get("urls", [])), "")
        try:
            data, fty_warehouses = publish_config(sid, data, origin, raw_base, exclusions)
            fty_fetched = sid, name, data
        except (OSError, ValueError) as error:
            fty_entry.update(ok=False, error=str(error))
    status["sources"] = [
        s for s in status["sources"]
        if s.get("id") != fty_entry["id"] and s.get("name") != fty_entry["name"]
    ]
    status["sources"].insert(0, fty_entry)

    subscriptions = [u for u in subscriptions if u.get("name") != fty_entry["name"]]
    fetched = [item for item in fetched if item[0] != fty_entry["id"]]
    if fty_entry["ok"]:
        if not fty_warehouses or any(field in fty_fetched[2] for field in TVBOX_KEYS):
            fty_warehouses.insert(0, fty_sub)
        subscriptions[:0] = fty_warehouses
        fetched.insert(0, fty_fetched)

    ok_count = sum(1 for s in status["sources"] if s.get("ok"))
    total = len(status["sources"])

    # 生成多仓订阅文件（影视仓"订阅/多仓"格式）
    sub_path = os.path.join(OUTPUT_DIR, "多仓订阅.json")
    with open(sub_path, "w", encoding="utf-8") as f:
        json.dump({"urls": subscriptions}, f, ensure_ascii=False, indent=2)

    # 生成聚合单仓文件（把所有成功源的 sites/lives/parses 合并成一个单仓）
    merged = merge_configs(fetched)
    merged_path = os.path.join(OUTPUT_DIR, "单仓聚合.json")
    if merged is not None:
        with open(merged_path, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        print(f"聚合单仓：{merged_path}（共 {len(merged.get('sites', []))} 个站点）")

    # 生成更新状态文件（时间取全部抓取完成之后）
    status["updated_at"] = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    with open(os.path.join(OUTPUT_DIR, "status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

    write_badge(ok_count, total)

    print("\n" + "=" * 50)
    print(f"本次更新：{ok_count}/{total} 个源成功")
    print(f"多仓订阅：{sub_path}")
    if ok_count == 0:
        print("没有任何源更新成功，返回非 0 退出码。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
