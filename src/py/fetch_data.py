# -*- coding: utf-8 -*-
"""fetch_data.py — CAPM-A股项目取数主流程
职责：
  1) 主窗口fixture：六股新浪hfq日收盘 + 沪深300指数（东财→东财备→新浪备的接口链）
  2) 扩展fixture（raw_ext）：六股新浪hfq OHLC + 指数OHLC，2015起，供十年稳健性附录
  3) 备胎尝试：H00300全收益指数、1年期国债收益率（失败回退常数rf并记录）
  4) yfinance镜像（当前网络常429）+ 两层比对（日历层/收益率层）
  5) 落盘 + SHA-256清单 + 元数据
幂等保护：所有fixture文件存在即跳过（防止重抓导致字节漂移、破坏SHA断言）；
强制重建需手动删除对应文件后重跑。
warm-up：start=2023-12-29，保证2024-01-02首个收益观测有前一收盘价。
"""
import sys, os, json, hashlib, datetime, time
sys.stdout.reconfigure(encoding='utf-8')

import warnings
warnings.filterwarnings('ignore')

import akshare as ak
import yfinance as yf
import pandas as pd

START = "20231229"          # warm-up起点（2023最后交易日）
END   = "20251231"
START_ISO, END_ISO = "2023-12-29", "2025-12-31"
EXT_START = "20150101"      # 十年扩展起点
EXT_START_ISO = "2014-12-01"  # 指数多取一个月保证首个差分点

STOCKS = {
    "600519": "贵州茅台", "600036": "招商银行", "300750": "宁德时代",
    "000333": "美的集团", "600276": "恒瑞医药", "600900": "长江电力",
}

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # src/py → 仓库根
D_RAW   = os.path.join(ROOT, "data", "raw")
D_MIRROR = os.path.join(ROOT, "data", "mirror")
D_META  = os.path.join(ROOT, "data", "meta")
D_EXT   = os.path.join(ROOT, "data", "raw_ext")
for d in (D_RAW, D_MIRROR, D_META, D_EXT):
    os.makedirs(d, exist_ok=True)

def fetch_retry(fn, *a, tries=4, waits=(5, 15, 30, 45), **kw):
    """带退避的重试包装: 接口瞬断/限流时不整体失败"""
    last = None
    for i in range(tries):
        try:
            return fn(*a, **kw)
        except Exception as e:
            last = e
            time.sleep(waits[min(i, len(waits) - 1)])
    raise last

def sina_sym(code):
    return ("sh" if code.startswith("6") else "sz") + code

META = {
    "fetch_time_utc8": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),
    "akshare_version": ak.__version__,
    "pandas_version": pd.__version__,
    "window": {"start": START_ISO, "end": END_ISO,
               "note": "start含warm-up日，收益序列首日为2024-01-02"},
    "adjust_choice": {"value": "hfq",
                      "reason": "后复权以上市日为锚，历史窗口内价格不随未来分红送转修订，fixture稳定性优于qfq"},
    "provider_incident": {
        "found": "2026-08-31 三源交叉验证（东财hfq × 新浪raw × 腾讯raw，招行样本）",
        "evidence": "非除权日东财hfq日收益被系统性压缩（2024-09-24招行：新浪+5.40%/腾讯+5.39% vs 东财+3.95%；全窗口485天中471天|Δr|>1bp）；新浪hfq与新浪raw非事件日收益一致（内部自洽）",
        "conclusion": "东财stock_zh_a_hist的hfq日收益不满足'因子在事件间恒定'的基本性质，不可用于收益率估计",
        "action": "主源切换为新浪stock_zh_a_daily(adjust=hfq)，canonical全部结果基于新浪数据",
        "third_party_scope": "个股层面全量第三方校验未建成（yfinance持续429），事故定位仅基于招行样本的三源对照；列为待办",
    },
    "mirror_status": "yfinance对抓取端持续HTTP 429，镜像未建成；第三方校验现状见provider_incident.third_party_scope",
    "endpoints": {},   # 每次运行实际发生的行为（skip/fetch）逐条记录
}

def save(df, folder, name):
    p = os.path.join(folder, name)
    df.to_csv(p, index=False, encoding="utf-8-sig")
    print(f"  saved {name} rows={len(df)}")
    return p

def sha256(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

# ---------- 1. 主窗口：六股新浪hfq（存在即跳过） ----------
print("[1/6] 主窗口 六股新浪hfq ...")
ak_stocks = {}
for code, cname in STOCKS.items():
    fpath = os.path.join(D_RAW, f"{code}_hfq.csv")
    if os.path.exists(fpath):
        keep = pd.read_csv(fpath)
        META["endpoints"][f"stock_zh_a_daily({sina_sym(code)})"] = {"adjust": "hfq", "rows": len(keep), "action": "skip_existing"}
        print(f"  skip existing {code}_hfq.csv rows={len(keep)}")
    else:
        df = fetch_retry(ak.stock_zh_a_daily, symbol=sina_sym(code),
                         start_date=START, end_date=END, adjust="hfq")
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        keep = df[["date", "close"]].copy()
        keep.insert(1, "code", code)
        keep["stock"] = cname
        save(keep, D_RAW, f"{code}_hfq.csv")
        META["endpoints"][f"stock_zh_a_daily({sina_sym(code)})"] = {"adjust": "hfq", "rows": len(keep), "action": "fetched"}
    ak_stocks[code] = keep

# ---------- 2. 主窗口：指数（存在即跳过；接口链东财→东财备→新浪备） ----------
print("[2/6] 主窗口 指数 ...")
IDX_PATH = os.path.join(D_RAW, "index_000300.csv")
def get_index(symbol, em_sym, tx_sym):
    try:
        df = fetch_retry(ak.index_zh_a_hist, symbol=symbol, period="daily",
                         start_date=START, end_date=END, tries=2, waits=(5, 10))
        df = df.rename(columns={"日期": "date", "收盘": "close"})
        src = "index_zh_a_hist"
    except Exception:
        try:
            df = fetch_retry(ak.stock_zh_index_daily_em, symbol=em_sym, tries=2, waits=(5, 10))
            src = "stock_zh_index_daily_em"
        except Exception:
            df = fetch_retry(ak.stock_zh_index_daily, symbol=tx_sym)
            src = "stock_zh_index_daily(sina)"
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df["close"] = pd.to_numeric(df["close"])
    df = df[(df["date"] >= START_ISO) & (df["date"] <= END_ISO)]
    return df[["date", "close"]].reset_index(drop=True), src

if os.path.exists(IDX_PATH):
    META["endpoints"]["index_000300"] = {"rows": len(pd.read_csv(IDX_PATH)), "endpoint": "stock_zh_index_daily(sina)", "action": "skip_existing"}
    print("  skip existing index_000300.csv")
else:
    idx, idx_src = get_index("000300", "sh000300", "sh000300")
    save(idx, D_RAW, "index_000300.csv")
    META["endpoints"]["index_000300"] = {"rows": len(idx), "endpoint": idx_src, "action": "fetched"}

try:
    hidx, h_src = get_index("H00300", "sh000300", "sh000300")
    if h_src == "index_zh_a_hist" and len(hidx) > 400:
        save(hidx, D_RAW, "index_H00300_tr.csv")
        META["endpoints"]["index_H00300"] = {"rows": len(hidx), "endpoint": h_src}
    else:
        raise ValueError(f"endpoint={h_src} 非全收益专属源, 不采用")
except Exception as e:
    print(f"  !! H00300获取失败: {str(e)[:60]} → 记为待办")
    META["endpoints"]["index_H00300"] = {"error": str(e)[:200]}

# ---------- 3. rf序列（best-effort，失败回退常数） ----------
print("[3/6] 无风险利率 ...")
rf_ok = False
try:
    rf = fetch_retry(ak.bond_china_yield, start_date=START_ISO, end_date=END_ISO)
    rf1y = rf[rf["曲线名称"].str.contains("国债", na=False) & (rf["日期"].astype(str) >= START_ISO)]
    piv = rf1y.pivot_table(values="1年", index="日期", aggfunc="last")
    piv = piv.reset_index().rename(columns={"日期": "date", "1年": "yield_1y_pct"})
    if len(piv) > 400:
        save(piv, D_RAW, "rf_cn1y.csv")
        rf_ok = True
        META["endpoints"]["bond_china_yield(1y)"] = {"rows": len(piv), "unit": "年化%"}
except Exception as e:
    META["endpoints"]["bond_china_yield(1y)"] = {"error": str(e)[:120]}
if not rf_ok:
    print("  !! 国债收益率接口不可用 → rf附录使用常数1.40%/252")
    META["endpoints"]["rf_fallback"] = {"constant_pct_annual": 1.40, "divisor": 252}

# ---------- 4. 扩展fixture：raw_ext 十年OHLC（存在即跳过） ----------
print("[4/6] 扩展 十年OHLC(新浪hfq) ...")
for code, cname in STOCKS.items():
    fpath = os.path.join(D_EXT, f"{code}_hfq_ohlc.csv")
    key = f"raw_ext/{code}_hfq_ohlc.csv"
    if os.path.exists(fpath):
        META["endpoints"][key] = {"rows": len(pd.read_csv(fpath)), "action": "skip_existing"}
        continue
    df = fetch_retry(ak.stock_zh_a_daily, symbol=sina_sym(code),
                     start_date=EXT_START, end_date=END, adjust="hfq")
    df = df[["date", "open", "high", "low", "close"]].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    save(df, D_EXT, f"{code}_hfq_ohlc.csv")
    META["endpoints"][key] = {"rows": len(df), "action": "fetched"}
    time.sleep(1)

IX_FULL = os.path.join(D_EXT, "index_000300_ohlc_full.csv")
if not os.path.exists(IX_FULL):
    idxf = fetch_retry(ak.stock_zh_index_daily, symbol="sh000300")
    idxf["date"] = pd.to_datetime(idxf["date"]).dt.strftime("%Y-%m-%d")
    idxf = idxf[(idxf.date >= EXT_START_ISO) & (idxf.date <= END_ISO)]
    idxf[["date", "open", "close", "high", "low"]].to_csv(IX_FULL, index=False, encoding="utf-8-sig")
    META["endpoints"]["raw_ext/index_000300_ohlc_full.csv"] = {"rows": len(idxf), "action": "fetched"}
else:
    META["endpoints"]["raw_ext/index_000300_ohlc_full.csv"] = {"rows": len(pd.read_csv(IX_FULL)), "action": "skip_existing"}

# ---------- 5. yfinance镜像（常429，尽力而为） ----------
print("[5/6] yfinance 镜像 ...")
yf_codes = {**{c: (f"{c}.SS" if c.startswith("6") else f"{c}.SZ") for c in STOCKS},
            "000300": "000300.SS"}
for code, ycode in yf_codes.items():
    try:
        df = yf.Ticker(ycode).history(start=START_ISO, end="2026-01-02", auto_adjust=False)
        if len(df) == 0:
            raise ValueError("empty history")
        out = df.reset_index()[["Date", "Close", "Adj Close"]].copy()
        dates = pd.to_datetime(out["Date"])
        dates = dates.dt.tz_convert(None) if getattr(dates.dt, "tz", None) else dates
        out["date"] = dates.dt.strftime("%Y-%m-%d")
        save(out[["date", "Close", "Adj Close"]], D_MIRROR, f"{code}_yfmirror.csv")
        META["endpoints"][f"yfinance({ycode})"] = {"rows": len(out)}
    except Exception as e:
        print(f"  !! yfinance {ycode}: {str(e)[:60]}")
        META["endpoints"][f"yfinance({ycode})"] = {"error": str(e)[:120]}

# ---------- 6. 两层比对 + 落盘 ----------
print("[6/6] 两层比对与落盘 ...")
cal_dates = set(pd.read_csv(IDX_PATH)["date"])
report = {"calendar_layer": {}, "return_layer": {}}
for code, cname in STOCKS.items():
    hfq = ak_stocks[code]
    s_dates = set(hfq["date"])
    report["calendar_layer"][code] = {
        "name": cname,
        "ak_days_in_window": int((pd.Series(sorted(s_dates)) >= START_ISO).sum()),
        "missing_vs_index": sorted(cal_dates - s_dates),
        "extra_vs_index": sorted(s_dates - cal_dates),
    }
    mpath = os.path.join(D_MIRROR, f"{code}_yfmirror.csv")
    if os.path.exists(mpath):
        mir = pd.read_csv(mpath)
        j = hfq[["date", "close"]].merge(mir[["date", "Adj Close"]], on="date").dropna()
        import numpy as _np
        ra = pd.Series(_np.log(j["close"].astype(float).values).diff(), index=j["date"])
        rb = pd.Series(_np.log(j["Adj Close"].astype(float).values).diff(), index=j["date"])
        d = (ra - rb).abs()
        report["return_layer"][code] = {
            "compared_days": int(d.notna().sum()),
            "gt_1pct_errors": [x for x in d[d > 0.01].index.astype(str).tolist()][:20],
            "between_1e4_and_1pct": int(((d > 1e-4) & (d <= 0.01)).sum()),
            "max_abs_diff": float(d.max(skipna=True)),
        }

pd.DataFrame([{ "item": k, "detail": json.dumps(v, ensure_ascii=False)} for k, v in
     list(report["calendar_layer"].items()) + list(report["return_layer"].items())]).to_csv(
     os.path.join(D_META, "crosscheck_report.csv"), index=False, encoding="utf-8")
with open(os.path.join(D_META, "fetch_metadata.json"), "w", encoding="utf-8") as f:
    json.dump(META, f, ensure_ascii=False, indent=2)

manifest = {}
for folder in (D_RAW, D_MIRROR, D_EXT):
    if os.path.isdir(folder):
        for fn in sorted(os.listdir(folder)):
            manifest[os.path.relpath(os.path.join(folder, fn), ROOT).replace(os.sep, "/")] = sha256(os.path.join(folder, fn))
with open(os.path.join(D_META, "sha256_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print("\n=== 取数完成 ===")
print("日历层缺失日:", {k: len(v["missing_vs_index"]) for k, v in report["calendar_layer"].items()})
print("收益率层>1%错误:", {k: len(v["gt_1pct_errors"]) for k, v in report["return_layer"].items()} or "镜像未建成,本轮无比对")
