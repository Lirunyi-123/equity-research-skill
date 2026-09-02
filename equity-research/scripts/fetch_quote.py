#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_quote.py — A股行情与估值快照（equity-research skill，尽力而为）

用法:
    python3 fetch_quote.py 600519
    python3 fetch_quote.py SH600519

数据源: 腾讯行情接口(主) → 东方财富 push2(备)。均为公开非官方接口，可能变动；
输出务必与东方财富/新浪 F10 网页抽查核对后才能写入报告。失败时打印 guidance，
改走网页采集，不得编造。北交所暂不支持，请走网页。仅标准库。
"""
import json
import re
import sys
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def parse_symbol(arg):
    s = arg.strip().upper()
    m = re.match(r"^(SH|SZ|BJ)?(\d{6})$", s)
    if not m:
        die(f"无法解析代码: {arg}（仅支持6位A股代码）")
    pre, code = m.group(1), m.group(2)
    if pre is None:
        if code.startswith("6"):
            pre = "SH"
        elif code[0] in "03":
            pre = "SZ"
        elif code[0] in "48":
            die("北交所代码暂不支持自动行情，请走网页采集")
        elif code[0] == "5":
            die("5开头是沪市基金/ETF代码，本skill仅覆盖上市公司股票", sym=None)
        else:
            die(f"无法识别代码归属: {code}（沪6/深0/3/创业板3/科创688/北4·8）", sym=None)
    if pre == "BJ":
        die("北交所代码暂不支持自动行情，请走网页采集")
    # 腾讯接口区分大小写，只认小写前缀
    return (pre + code).lower(), pre.lower(), code


def die(msg, sym=None):
    page = f"quote.eastmoney.com/{sym}.html" if sym else "东方财富/新浪个股页"
    print(json.dumps({"ok": False, "error": msg,
                      "guidance": f"改走网页采集：WebFetch 东方财富个股页 {page} "
                                  "或新浪财经个股页，记录现价/市值/PE/PB 及访问时间"},
                     ensure_ascii=False))
    sys.exit(1)


def http_get(url, decode="utf-8"):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=10).read().decode(decode, "ignore")


def num(fields, i):
    try:
        v = float(fields[i])
        return v if v != 0 else None
    except (ValueError, IndexError):
        return None


def fetch_tencent(sym):
    raw = http_get(f"https://qt.gtimg.cn/q={sym}", decode="gbk")
    m = re.search(r'"(.*)"', raw)
    if not m:
        raise RuntimeError("腾讯接口返回为空或格式变化")
    f = m.group(1).split("~")
    # 需要 1(名称) 3(价) 39(PE) 44/45(市值) 46(PB)，共47个字段
    if len(f) < 47 or not f[1] or not num(f, 3):
        raise RuntimeError(f"腾讯接口字段缺失(len={len(f)})")
    return {
        "ok": True, "source": "qt.gtimg.cn", "symbol": sym, "name": f[1],
        "price": num(f, 3), "pe_ttm": num(f, 39),
        "float_mcap_yi": num(f, 44), "total_mcap_yi": num(f, 45), "pb": num(f, 46),
        "quote_time": f[30] if len(f) > 30 else None,
    }


def fetch_eastmoney(mkt, code):
    secid = f"{'1' if mkt == 'sh' else '0'}.{code}"
    fields = "f43,f57,f58,f116,f117,f163,f167"
    data = json.loads(http_get(
        f"https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields={fields}"))
    d = data.get("data") or {}
    if not d.get("f58"):
        raise RuntimeError("东方财富接口返回为空")
    px = d.get("f43")
    pe = d.get("f163")
    pb = d.get("f167")

    def scale100(v):
        # push2 接口的比率和价格字段为实际值×100
        return v / 100 if isinstance(v, (int, float)) else None

    return {
        "ok": True, "source": "push2.eastmoney.com", "symbol": f"{mkt}{code}",
        "name": d.get("f58"), "price": scale100(px),
        "pe_ttm": scale100(pe), "pb": scale100(pb),
        "total_mcap_yi": (d.get("f116") / 1e8 if isinstance(d.get("f116"), (int, float)) else None),
        "float_mcap_yi": (d.get("f117") / 1e8 if isinstance(d.get("f117"), (int, float)) else None),
        "quote_time": None,
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sym, mkt, code = parse_symbol(sys.argv[1])
    result = None
    errors = []
    import time
    for attempt in range(2):  # 出网连接偶发被重置，每源重试一次
        for fetcher in (lambda: fetch_tencent(sym), lambda: fetch_eastmoney(mkt, code)):
            try:
                result = fetcher()
                break
            except Exception as e:  # noqa: BLE001 — 降级链：记录错误换下一源
                errors.append(f"第{attempt+1}次: {e}")
        if result:
            break
        time.sleep(1)
    if not result:
        die("；".join(errors), sym=sym)
    result["unit_note"] = "价格元；市值亿元；PE/PB为倍数。来自非官方公开接口，用前与F10网页抽查核对。"
    result["errors_ignored"] = errors or None
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
