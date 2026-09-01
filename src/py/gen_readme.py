# -*- coding: utf-8 -*-
"""gen_readme.py — 从results/tables/机器精度表自动生成README(禁手打数字)
运行: venv python src/py/gen_readme.py  → 生成 README.md
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd, numpy as np
from scipy import stats

NAMES = {'600519':'贵州茅台','600036':'招商银行','300750':'宁德时代',
         '000333':'美的集团','600276':'恒瑞医药','600900':'长江电力'}
ORDER = ['300750','600276','600519','600036','000333','600900']   # 按β降序展示

def fmt_p(p):
    if p == 0: return "<1e-300"
    if p < 1e-4: return f"{p:.2e}"
    return f"{p:.4f}"

can = pd.read_csv('results/tables/base_canonical.machine.csv', dtype={'code':str}).set_index('code').loc[ORDER]
rob = pd.read_csv('results/tables/robust_hac.machine.csv', dtype={'code':str})
rd = rob[rob.track=='daily'].set_index('code').loc[ORDER]
rw = rob[rob.track=='weekly'].set_index('code')
sub = pd.read_csv('results/tables/subsample_year.machine.csv', dtype={'code':str})
per = pd.read_csv('results/tables/extended_periods.machine.csv', dtype={'code':str})
chow = pd.read_csv('results/tables/chow924.machine.csv', dtype={'code':str})
rf = pd.read_csv('results/tables/rf_appendix.machine.csv', dtype={'code':str})
ret = pd.read_csv('data/processed/returns_daily.csv')
retw = pd.read_csv('data/processed/returns_weekly.csv')

# ---- 表1 canonical ----
rows = ["| 股票 | n | α | p(α) | β | p(β) | R² | JB p |","|---|---|---|---|---|---|---|---|"]
for c in ORDER:
    r = can.loc[c]
    rows.append(f"| {NAMES[c]} | {int(r.n)} | {r.alpha:.6f} | {fmt_p(r.p_alpha)} | "
                f"{r.beta:.4f} | {fmt_p(r.p_beta)} | {r.r2*100:.1f}% | {fmt_p(r.jb_p)} |")
TBL_CANONICAL = "\n".join(rows)

# ---- 表2 robust ----
rows = ["| 股票 | β | SE(OLS) | SE(HC3) | SE(NW) | p(OLS) | p(HC3) | p(NW) |","|---|---|---|---|---|---|---|---|"]
for c in ORDER:
    r = rd.loc[c]
    rows.append(f"| {NAMES[c]} | {r.beta:.4f} | {r.se_ols:.4f} | {r.se_hc3:.4f} | {r.se_nw:.4f} | "
                f"{fmt_p(r.p_ols)} | {fmt_p(r.p_hc3)} | {fmt_p(r.p_nw)} |")
TBL_ROBUST = "\n".join(rows)

# ---- 表3 分年 ----
rows = ["| 股票 | 2024 β (p) | 2025 β (p) |","|---|---|---|"]
for c in ORDER:
    a = sub[(sub.code==c)&(sub.year==2024)].iloc[0]; b = sub[(sub.code==c)&(sub.year==2025)].iloc[0]
    rows.append(f"| {NAMES[c]} | {a.beta:.3f} ({fmt_p(a.p)}) | {b.beta:.3f} ({fmt_p(b.p)}) |")
TBL_SUBSAMPLE = "\n".join(rows)

# ---- 表4 十年分时期 ----
piv = per.pivot(index='period', columns='code', values='beta')
rows = ["| 时期 | " + " | ".join(NAMES[c] for c in ORDER) + " |", "|---|" + "---|"*6]
for p in ['2015-2017','2018-2020','2021-2023','2024-2025']:
    rows.append(f"| {p} | " + " | ".join("—" if pd.isna(piv.loc[p, c]) else f"{piv.loc[p, c]:.2f}" for c in ORDER) + " |")
TBL_PERIODS = "\n".join(rows)

# ---- 表5 周频对照 ----
rows = ["| 股票 | β(日) | β(周) | p_NW(日) | p_NW(周) | R²(日) | R²(周) |","|---|---|---|---|---|---|---|"]
for c in ORDER:
    w = rw.loc[c]
    rows.append(f"| {NAMES[c]} | {rd.loc[c,'beta']:.3f} | {w.beta:.3f} | {fmt_p(rd.loc[c,'p_nw'])} | "
                f"{fmt_p(w.p_nw)} | {can.loc[c,'r2']*100:.1f}% | {w.r2*100:.1f}% |")
TBL_WEEKLY = "\n".join(rows)

# ---- 表6 α显著性(三套SE×两频率) ----
rows = ["| 股票 | α(日) | p(OLS) | p(HC3) | p(NW) | p(NW·周频) |","|---|---|---|---|---|---|"]
for c in ORDER:
    rows.append(f"| {NAMES[c]} | {rd.loc[c,'alpha']:.6f} | {fmt_p(rd.loc[c,'p_alpha_ols'])} | "
                f"{fmt_p(rd.loc[c,'p_alpha_hc3'])} | {fmt_p(rd.loc[c,'p_alpha_nw'])} | {fmt_p(rw.loc[c,'p_alpha_nw'])} |")
rows.append("")
_mt_w = [rw.loc['600519', k] for k in ('p_alpha_ols', 'p_alpha_hc3', 'p_alpha_nw')]
_mt_d = [rd.loc['600519', k] for k in ('p_alpha_ols', 'p_alpha_hc3')]
rows.append(f"> α显著性（三种标准误×两个频率）：五只股票均无法拒绝α=0。唯一例外是贵州茅台的负α——周频下三种标准误全部显著（p≈{min(_mt_w):.3f}-{max(_mt_w):.3f}），日频下仅Newey-West显著（p≈{rd.loc['600519','p_alpha_nw']:.3f}）、OLS/HC3不显著（p≈{min(_mt_d):.3f}-{max(_mt_d):.3f}）。两种结果并列，不替读者选择。")
TBL_ALPHA = "\n".join(rows)

vals = {
    "{{N_DAILY}}": str(len(ret)),
    "{{N_WEEKLY}}": str(len(retw)),
    "{{B_MAX}}": f"{can.beta.max():.2f}",
    "{{B_MIN}}": f"{can.beta.min():.2f}",
    "{{R2_MIN}}": f"{can.r2.min()*100:.1f}%",
    "{{RF_MAXDELTA}}": f"{rf.delta.abs().max():.1e}",
    "{{BW_LIST_D}}": " / ".join(f"{NAMES[c]} {int(rd.loc[c,'lag_used'])}" for c in ORDER),
    "{{TBL_WEEKLY}}": TBL_WEEKLY,
    "{{TBL_ALPHA}}": TBL_ALPHA,
    "{{MT_A_NW_D}}": f"{rd.loc['600519','p_alpha_nw']:.3f}",
    "{{MT_A_W_RANGE}}": f"{rw.loc['600519','p_alpha_nw']:.3f}-{rw.loc['600519','p_alpha_ols']:.3f}",
    "{{YANGDI_LOWBETA}}": (lambda g: f"{len(g)}个年度β中{int((g.beta<0.4).sum())}个低于0.4")(
        pd.read_csv('results/tables/extended_annual.machine.csv', dtype={'code':str}).query("code=='600900'")),
    "{{CHANGDIAN_HC3_P}}": f"{rd.loc['600900','p_hc3']:.3f}",
    "{{CHANGDIAN_NW_P}}": f"{rd.loc['600900','p_nw']:.4f}",
    "{{SE_RATIO_RANGE}}": (lambda rs: f"{min(rs):.1f}-{max(rs):.1f}")(
        (rd.se_hc3/rd.se_ols).tolist() + (rd.se_nw/rd.se_ols).tolist()),
    "{{CHOW_MIN_P}}": f"{chow.p.min():.3f}",
    "{{TBL_CANONICAL}}": TBL_CANONICAL,
    "{{TBL_ROBUST}}": TBL_ROBUST,
    "{{TBL_SUBSAMPLE}}": TBL_SUBSAMPLE,
    "{{TBL_PERIODS}}": TBL_PERIODS,
}
tpl = open('docs/README.template.md', encoding='utf-8').read()
out = tpl
for k, v in vals.items():
    out = out.replace(k, v)
import re
leftover = re.findall(r"\{\{[A-Z_0-9]+\}\}", out)
assert not leftover, f"未填充占位符: {leftover}"
open('README.md', 'w', encoding='utf-8', newline='\n').write(out)
print("README.md 生成完成,", len(out), "字符; 占位符全部填充")

# ---- 统计语言lint: 拦截已知错误表述(统计术语误用/拼写) ----
lint_terms = ["显著为0", "显著为 0", "CAMP", "自由度样本"]
hits = [b for b in lint_terms if b in out]
print("语言lint:", "通过" if not hits else f"命中 -> {hits}")
