# -*- coding: utf-8 -*-
"""incident_check.py — 数据源事故的联网复跑核验
背景: 2026-08-31开发中发现东方财富stock_zh_a_hist的hfq序列在非除权日的日收益
     相对新浪/腾讯被系统性压缩(README设计决策1)。本脚本从三个公开源重拉招商银行
     (600036) 2023-12-29~2025-12-31日线, 重算并输出对照证据。
输出: evidence/incident_check.csv (逐日三源对数收益与差值)
退出码: 0=核验完成; 2=接口不可用(网络/限流), 此时README声明以存档记录为准
"""
import sys, os, time
sys.stdout.reconfigure(encoding='utf-8')
import warnings; warnings.filterwarnings('ignore')
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # evidence/ → 仓库根
os.makedirs('evidence', exist_ok=True)

import akshare as ak
import pandas as pd
import numpy as np

def logret(s):
    ser = s if isinstance(s, pd.Series) else pd.Series(np.asarray(s, dtype=float))
    return np.log(ser.astype(float)).diff()

def try_fetch(name, fn, tries=3):
    for i in range(tries):
        try:
            return fn()
        except Exception as e:
            print(f"  [{name}] 第{i+1}次失败: {type(e).__name__} {str(e)[:60]}")
            time.sleep(5 * (i + 1))
    return None

print("[1/3] 东财 hfq (stock_zh_a_hist) ...")
em = try_fetch("东财", lambda: ak.stock_zh_a_hist(symbol="600036", period="daily",
        start_date="20231229", end_date="20251231", adjust="hfq"))
print("[2/3] 新浪 hfq (stock_zh_a_daily) ...")
sina = try_fetch("新浪", lambda: ak.stock_zh_a_daily(symbol="sh600036",
        start_date="20231229", end_date="20251231", adjust="hfq"))
print("[3/3] 腾讯 (stock_zh_a_hist_tx) ...")
tx = try_fetch("腾讯", lambda: ak.stock_zh_a_hist_tx(symbol="sh600036",
        start_date="20231229", end_date="20251231", adjust=""))

if sina is None:
    print("主源不可用, 无法核验 → 退出码2")
    sys.exit(2)

s = sina.copy(); s["date"] = pd.to_datetime(s["date"]).dt.strftime("%Y-%m-%d")
df = pd.DataFrame({"date": s["date"], "sina_hfq_ret": logret(s["close"].values).values})

if tx is not None:
    t = tx.copy(); t["date"] = pd.to_datetime(t["date"]).dt.strftime("%Y-%m-%d")
    t = t.set_index("date")
    df["tx_ret"] = t["close"].pipe(logret).reindex(df["date"]).values

if em is not None:
    e = em.rename(columns={"日期": "date", "收盘": "close"}).copy()
    e["date"] = pd.to_datetime(e["date"]).dt.strftime("%Y-%m-%d")
    e = e.set_index("date")
    df["em_hfq_ret"] = e["close"].pipe(logret).reindex(df["date"]).values
    df["delta_em_vs_sina"] = (df["em_hfq_ret"] - df["sina_hfq_ret"]).abs()

df.to_csv("evidence/incident_check.csv", index=False, encoding="utf-8")
print(f"\n已写 evidence/incident_check.csv, {len(df)}行")

if em is not None:
    d = df.dropna(subset=["delta_em_vs_sina"])
    n_gt = int((d["delta_em_vs_sina"] > 1e-4).sum())
    mx = d.loc[d["delta_em_vs_sina"].idxmax()]
    day924 = d[d["date"] == "2024-09-24"]
    print(f"核验结论: 可比{len(d)}天中 |Δr|>1bp 共{n_gt}天")
    print(f"  最大偏差日: {mx['date']} 东财{mx['em_hfq_ret']*100:.2f}% vs 新浪{mx['sina_hfq_ret']*100:.2f}% (Δ={mx['delta_em_vs_sina']*100:.2f}pp)")
    if len(day924):
        r0 = day924.iloc[0]
        print(f"  2024-09-24: 东财{r0['em_hfq_ret']*100:.2f}% vs 新浪{r0['sina_hfq_ret']*100:.2f}%")
    print("  → 东财hfq日收益压缩现象: " + ("复现成立" if n_gt > 100 else "未复现(东财可能已修复), README声明需相应降级"))
else:
    print("东财接口本次不可用(限流): 本次仅新浪/腾讯可用, 事故核验以存档记录为准")
    sys.exit(2)
